'''
Section classes.
'''

import math
import copy

from .point import Pt


class Section:
	'''Cross-sections to be swept along a path to make components.'''

	# Note: When drawing, make span of all sections slightly smaller than stated
	# to avoid floating point errors when lofting.
	eps = 0

	def inv(self,mem_D=20):
		'''Return a copied section with inverted height in Z (if possible).'''
		# This is only applicable for 2.5D sections (not TubeSec).
		# Will offset appropriately based on mem_D so that membrane is below z=0.

		copied = copy.deepcopy(self) # Must use deepcopy to deepcopy Points
		if hasattr(copied,'H'):
			copied.H = -copied.H
		copied.offset.Z = -mem_D - copied.offset.Z
		return copied

	def __eq__(self, other): 
		# Equality is used to determine whether to use loft or sweep
		return self.__dict__ == other.__dict__

	def __neg__(self):
		# Equivalent to calling self.inv()
		return self.inv()


class RecSec(Section):
	def __init__(self, W=250, H=50, offset=(0,0,0)):
		'''Constructor for Rectangular Section.'''
		self.W = W
		self.H = H
		self.offset = Pt(*offset) if isinstance(offset,tuple) else offset
		self.span = W # Used to avoid loft self-intersections
		h = abs(min(H,W)*1e-6) # SI height
		w = abs(max(H,W)*1e-6) # SI width
		# Multiply following by mu*L to obtain resistance in SI
		# This has units of 1/(m^4)
		self.res_muL = 12/((1-0.63*(h/w))*h**3*w)

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		W = self.W - self.eps
		H = self.H
		px = [0,0,0,0]
		py = [-W/2,W/2,W/2,-W/2]
		pz = [0,0,H,H]
		px = [x+self.offset.x for x in px]
		py = [y+self.offset.y for y in py]
		pz = [z+self.offset.z for z in pz]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point
		
		# Draw in backend
		backend = circuit.design.backend
		comp = circuit.component
		segs = []
		for i in range(len(pts)):
			segs.append(backend.create_seg(comp,pts[i-1],pts[i]))
		path = backend.create_path(comp,segs)
		return path


class CurveSec(Section):
	def __init__(self, W=250, H=50, R=None, offset=(0,0,0)):
		'''Constructor for a Curvilinear section.'''
		self.W = W
		self.H = H
		self.R = abs(H) if R is None else abs(R)
		self.offset = Pt(*offset) if isinstance(offset,tuple) else offset
		self.span = W # Used to avoid loft self-intersections
		h = abs(H*1e-6) # SI height
		w = abs(W*1e-6) # SI width
		r = abs(self.R*1e-6) # SI radius
		# Multiply following by mu*L to obtain resistance in SI
		# This has units of 1/(m^4)
		# Originally, used the 2*P^2/A^3 approximation, but that is practically 
		# equivalent to the parallel infinite plate approximation.
		# The infinite parallel plate approximation underestimates the true resistance.
		# P = 2*w + 2*h - 4*r + math.pi*r
		# A = w*h - 2*r*r + 0.5*math.pi*r*r
		# self.res_muL = 2*(P*P)/(A*A*A)
		# A better approximation is the rectangle approximation, which is used above.
		# Note: the rectangle approximation ALSO underestimates true resistance 
		# (due to chamfers), but not by much.
		self.res_muL = 12/((1-0.63*(h/w))*h**3*w)

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		W = self.W - self.eps
		H = self.H
		R = self.R
		px = [0,0,0,0]
		py = [-W/2,W/2,W/2,-W/2]
		pz = [0,0,H,H]
		px = [x+self.offset.x for x in px]
		py = [y+self.offset.y for y in py]
		pz = [z+self.offset.z for z in pz]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point

		# Draw in backend
		backend = circuit.design.backend
		comp = circuit.component
		segs = []
		eps = 1e-3

		# Add fillets at top
		if abs(R) - abs(H) < 1: # Fully curved top
			# Create oversized side segments (to allow filleting)
			segs = [backend.create_seg(comp,pts[3],pts[0]-(0,0,H)),
				backend.create_seg(comp,pts[0],pts[1]),
				backend.create_seg(comp,pts[1]-(0,0,H),pts[2]),
				backend.create_seg(comp,pts[2],pts[3])]
			# Fillet
			_, arc1, segs[3] = backend.fillet_2_segs(comp,segs[2],segs[3],R)
			segs[3], arc2, _ = backend.fillet_2_segs(comp,segs[3],segs[0],R)
			objs = [segs[1], arc1, segs[3], arc2] # Add in order
			path = backend.create_path(comp,objs)
			return path
		else: # Partially filleted top
			# Create segments
			for i in range(len(pts)):
				segs.append(backend.create_seg(comp,pts[i-1],pts[i]))
			# Fillet
			segs[2], arc1, segs[3] = backend.fillet_2_segs(comp,segs[2],segs[3],R)
			segs[-1], arc2, segs[0] = backend.fillet_2_segs(comp,segs[-1],segs[0],R)
			objs = segs[:3]+[arc1]+[segs[3]]+[arc2] # Add in order
			path = backend.create_path(comp,objs)
			return path


class TrapzSec(Section):
	def __init__(self, W=250, H=50, Wt=None, Ht=None, offset=(0,0,0)):
		'''Constructor for Trapezoidal Section.'''
		self.W = W 
		self.H = H
		# Height and Width of tapered section is Ht and Wt
		self.Wt = W-2*abs(H) if Wt is None else Wt
		self.Ht = math.copysign((W-self.Wt)/2,H) if Ht is None else Ht 
		self.offset = Pt(*offset) if isinstance(offset,tuple) else offset
		self.span = W # Used to avoid loft self-intersections

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		W = self.W - self.eps
		H = self.H
		Wt = self.Wt
		Ht = self.Ht
		dW = (W-Wt)/2 # half Width difference
		px = [0,0,0,0,0,0]
		py = [-W/2+dW,W/2-dW,W/2,W/2,-W/2,-W/2]
		pz = [H,H,H-Ht,0,0,H-Ht]
		px = [x+self.offset.x for x in px]
		py = [y+self.offset.y for y in py]
		pz = [z+self.offset.z for z in pz]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point

		# Draw in backend
		backend = circuit.design.backend
		comp = circuit.component
		segs = []
		for i in range(len(pts)):
			if (pts[i-1]-pts[i]).m > 1e-3: continue
			segs.append(backend.create_seg(comp,pts[i-1],pts[i]))
		path = backend.create_path(comp,segs)
		return path


class TubeSec(Section):
	def __init__(self, R=250, offset=(0,0,0)):
		'''Constructor for a Tube section (also used in Vias).'''
		self.R = R
		self.offset = Pt(*offset) if isinstance(offset,tuple) else offset
		self.span = 2*R # Used to avoid loft self-intersections
		
		r = abs(self.R*1e-6) # SI radius
		# Multiply following by mu*L to obtain resistance in SI
		# This has units of 1/(m^4)
		self.res_muL = 8/(math.pi*r**4)

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Draw this by drawing a box normal to x axis, then fillet edges
		R = self.R - self.eps
		px = [0,0,0,0]
		py = [-R,R,R,-R]
		pz = [-R,-R,R,R]
		px = [x+self.offset.x for x in px]
		py = [y+self.offset.y for y in py]
		pz = [z+self.offset.z for z in pz]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point

		# Special case for vertical vias
		# Other Sections do not have this ability to travel in Z axis
		if abs(u.z) > .5:
			pts = [Pt(pz[i],py[i],0) for i in range(len(px))]
			pts = [pt+pc for pt in pts] # Offset by center point

		# Draw in backend
		backend = circuit.design.backend
		comp = circuit.component
		objs = []
		for i in range(len(pts)):
			seg1 = backend.create_seg(comp,pts[i-1],pts[i])
			seg2 = backend.create_seg(comp,pts[i],pts[(i+1)%4])
			seg1,fillet,seg2 = backend.fillet_2_segs(comp,seg1,seg2,R)
			objs.append(fillet)
		path = backend.create_path(comp,objs)
		return path
