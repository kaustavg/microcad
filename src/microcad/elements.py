'''
Elements classes.
'''
import math
import copy

from .point import Pt
from .section import *

class Trace:
	def __init__(self,circuit,pts,secs=None,**kwargs):
		'''Constructor for a trace.'''
		self.circuit = circuit
		self.pts = [Pt(*pt) if isinstance(pt,tuple) else pt for pt in pts]
		pts = self.pts
		if secs is None: # Use default if no sections are passed
			secs = circuit.params['trace_sec']
		if isinstance(secs,Section): # Expand sections to fill list
			secs = [secs for i in range(len(pts))]
		assert len(pts) == len(secs)
		self.secs = secs
		self.params = circuit.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]

		# Drawing parameters
		eps = 1e-3
		minR = 0 # Minimum inner edge radius ##TBD FIX THIS IT'S TOO HIGH
		Rs = self.params['trace_R']
		if not isinstance(Rs,list): # Expand Rs to fill list
			Rs = [Rs for i in range(len(pts))]
		assert len(pts) == len(Rs)
		# Avoid self-intersections by ensuring R>sec.span/2
		Rs = [max(Rs[i],secs[i].span/2+minR) for i in range(len(pts))]
		# Check for length mismatches
		assert len(pts) == len(secs)
		assert len(pts) == len(Rs)
		'''
		Generate the whole segs w/ pts and normals, then sweep or loft pieces

		segs: sketchlines or sketcharcs
		draws = tuples of sec, pt, normal (startdraw of segs[i])

		for points range(1,end-1):
			Compute isColinear
			Create nextseg
			if not colinear:
				create (fillet,fstart,fend) with segs[-1],nextseg
				append fillet to segs
				append (secs[i],fstart,us[i-1]) to draws
			else
				fend = pt[i]
			append nextseg to segs
			append (secs[i],fend,us[i]) to draws
		append (secs[-1],pts[-1],us[-1]) to draws

		# Now step through the lists and identify areas to sweep or loft
		startind = 0
		for i in range(len(segsecs)-1)
			if segsecs[i] != segsecs[i+1]:
				sweep segs[startind:i], draw[i]
				loft segs[i],segs[i+1], draw[i], draw[i+1]
				startind = i+1
		sweep segs[startind:],draw(secs[-1],segpts[-1],segnors[-1])
		# Note if last seg is a loft, above line will have startind at end
		'''
		backend = circuit.design.backend
		comp = circuit.component
		# Compute unit normals
		us = []
		for i in range(len(pts)-1):
			d = pts[i+1]-pts[i]
			us.append(d/d.m)
		
		# Initialize growing lists of segs and draw tuples
		segs = [backend.create_seg(comp,pts[0],pts[1])]
		draws = [(secs[0],pts[0],us[0])] # Contains the startdraws of segs[i]

		# Step through points
		for i in range(1,len(pts)-1):
			isColinear = (us[i]-us[i-1]).m < eps
			nextseg = backend.create_seg(comp,pts[i],pts[i+1])
			if not isColinear:
				segs[-1],fillet,nextseg,fstart,fend = backend.fillet_2_segs(
					comp,segs[-1],nextseg,Rs[i],return_endpts=True)
				if fillet is not None:
					segs.append(fillet)
					draws.append((secs[i],fstart,us[i-1]))
				segs.append(nextseg)
				draws.append((secs[i],fend,us[i]))
			else: # Colinear
				segs.append(nextseg)
				draws.append((secs[i],pts[i],us[i]))
		# Add final draw
		draws.append((secs[-1],pts[-1],us[-1]))

		# Now step through segments and sweep or loft as needed
		trace = []
		startind = 0
		for i in range(len(segs)): # Note: len(draws)=1+len(segs)
			isLoft = draws[i][0] != draws[i+1][0]
			span = draws[i][0].span
			m = (draws[i][1] - draws[i+1][1]).m
			# print(2*m**2/span**2 + draws[i][2].dot(draws[i+1][2])) # Cos rule
			# isRev = (not isLot) and (eps > abs(2*m**2/span**2+)
			if isLoft: # Must loft
				# Sweep segs since last loft (startind) if there are any
				if startind < i:
					path = backend.create_path(comp,segs[startind:i])
					sweep = backend.create_sweep(comp,path,
						draws[i][0].draw(circuit,draws[i][1],draws[i][2]))
					trace.append(sweep)
				# Loft this segment
				loftpath = backend.create_path(comp,segs[i:i+1]) # TODO: does it need to be a path?
				loftdraws = [draws[i][0].draw(circuit,draws[i][1],draws[i][2]),
					draws[i+1][0].draw(circuit,draws[i+1][1],draws[i+1][2])]
				loft = backend.create_loft(comp,loftpath,loftdraws)
				trace.append(loft)
				startind = i+1

		# Finally, if we hit the end sweep all that remains
		if startind < len(segs):
			path = backend.create_path(comp,segs[startind:])
			draw = draws[-1][0].draw(circuit,draws[-1][1],draws[-1][2])
			sweep = backend.create_sweep(comp,path,draw)
			trace.append(sweep)

		# Draw endcaps (TBD: 'square' is only axis aligned right now)
		# TBD: trace_cap is only accurate for RecSec, others make rectangular cap!
		if self.params['trace_cap'] == 'round':
			circuit.V(pts[0]+secs[0].offset,zspan=[pts[0].z,pts[0].z+secs[0].H],
				via_R=secs[0].span/2)
			circuit.V(pts[-1]+secs[-1].offset,zspan=[pts[-1].z,pts[-1].z+secs[-1].H],
				via_R=secs[-1].span/2)
		elif self.params['trace_cap'] == 'square':
			circuit.T([pts[0]-(secs[0].span/2,0),pts[0]+(secs[0].span/2,0)],
				secs=secs[0],trace_cap='none')
			circuit.T([pts[-1]-(secs[-1].span/2,0),pts[-1]+(secs[-1].span/2,0)],
				secs=secs[-1],trace_cap='none')

		# Set the pins
		self.P1 = pts[0]
		self.P2 = pts[-1]
		self.C = self.P1 % self.P2

class Via:
	def __init__(self,circuit,pt,zspan=None,**kwargs):
		'''Constructor for a via.'''
		self.circuit = circuit
		self.pt = Pt(*pt) if isinstance(pt,tuple) else pt
		pt = self.pt
		self.params = circuit.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]
		self.zspan = [0, self.params['sub_H']] if zspan is None else zspan
		zspan = self.zspan
		
		# Draw
		R = self.params['via_R']
		start = Pt(pt.x,pt.y,zspan[0])
		end = Pt(pt.x,pt.y,zspan[1])
		circuit.T([start,end],secs=TubeSec(R=R),trace_cap=None)

		# Set the pin
		self.C = pt

class Transistor:
	def __init__(self,circuit,pt,anchor='C',rotation=0,invert=False,**kwargs):
		'''Constructor for transistor.'''
		# Oriented such that channel is UD and gate is LR.
		self.circuit = circuit
		self.pt = Pt(*pt) if isinstance(pt,tuple) else pt
		pt = self.pt
		self.anchor = anchor
		self.rotation = rotation
		self.invert = invert # If true, flip each channel section in Z
		self.params = circuit.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]

		# Drawing parameters
		self.chan_sec = self.params['chan_sec']
		self.gate_sec = self.params['gate_sec']
		if invert: # TBD: Make inversion a method which returns a new sec
			self.chan_sec = copy.deepcopy(self.chan_sec)
			self.chan_sec.H *= -1
			self.gate_sec = copy.deepcopy(self.gate_sec)
			self.gate_sec.H *= -1
		slop = self.params['slop']
		L = self.gate_sec.span
		W = self.chan_sec.span
		H = self.chan_sec.H

		# Compute draw points
		points = [Pt(), Pt(0,L/2+slop), Pt(0,-L/2-slop),
			Pt(-W/2-slop,0), Pt(W/2+slop,0),
			Pt(0,L/2),Pt(0,-L/2)]
		anchors = ['C','S','D','G1','G2','P1','P2']
		a = points[anchors.index(anchor)]
		# Center over anchor
		points = [point - a for point in points]
		# Rotate and shift as needed
		points = [pt+point.rotate(rotation) for point in points]

		# Draw
		circuit.T([points[1],points[5],points[6],points[2]],
			secs=self.chan_sec,trace_cap='none')
		circuit.T([points[3],points[4]],secs=self.gate_sec,trace_cap='none')

		# Set the pins
		self.C = points[0]
		self.S = points[1]
		self.D = points[2]
		self.G1 = points[3]
		self.G2 = points[4]
		self.P1 = points[5]
		self.P2 = points[6]

class Resistor:
	def __init__(self,circuit,pt,val,anchor='L',rotation=0,justify='left',**kwargs):
		'''Constructor for resistor (left-right).'''
		self.circuit = circuit
		self.pt = Pt(*pt) if isinstance(pt,tuple) else pt
		pt = self.pt
		self.anchor = anchor
		self.rotation = rotation
		self.params = circuit.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]
		self.val = val
		self.justify = justify

		# Drawing parameters
		MU = self.params['fluid_Mu']
		L = self.params['res_L']
		R_sec = self.params['res_sec']
		T_sec = self.params['trace_sec']
		if R_sec.H < 0:# TBD: Make inversion a method which returns a new sec
			T_sec = copy.deepcopy(T_sec)
			T_sec.H *= -1
		R = R_sec.span
		T = T_sec.span

		# Compute the number of wiggles that fit
		n = math.floor((L-T)//(R*4))
		# Compute the centerline distance with minimum wiggle amplitude
		wiggle_dist = n*(2*R + math.pi*R)
		# Compute the the wedge distances for entry and exit
		wedge_dist = (L-(n*R*4))/2
		# Compute the resistance with[(secs[0],pts[0],us[0])]  minimum wiggle amplitude
		min_res = MU * (R_sec.res_muL*wiggle_dist
			+ (R_sec.res_muL+T_sec.res_muL)*wedge_dist)
		min_res *= 1e-18 # Convert from 1/(m^4)*Pa*s*um to kPa*s/ul
		rem_res = val - min_res # Res to be gained in wiggle amplitude
		assert rem_res > 0, "Resistance too small."
		wiggle_amp = rem_res / (MU*R_sec.res_muL*n*2) * 1e18 # um

		# Place points
		points = [Pt()]
		secs = [T_sec]
		last_pt = Pt()+((L - (n*R*4))/2 ,0)
		points.append(last_pt) # Inlet wedge
		secs.append(R_sec)
		for i in range(n):
			wiggle = [
				last_pt+(R,0),
				last_pt+(R,R+wiggle_amp),
				last_pt+(3*R,R+wiggle_amp),
				last_pt+(3*R,0),
				last_pt+(4*R,0)]
			points += wiggle # Add the new wiggle
			secs += [R_sec for i in range(len(wiggle))]
			last_pt = wiggle[-1]
		points.append(Pt(L,0)) # Outlet wedge
		secs.append(T_sec)

		# Flip if justified right
		if justify == 'right':
			points = [Pt(point.x,-point.y,point.z) for point in points]

		# Determine anchor
		anchor_pts = [Pt(), Pt(L/2,0), Pt(L,0)]
		anchors = ['L','C','R']
		a = anchor_pts[anchors.index(anchor)]
		# Center over anchor
		points = [point - a for point in points]
		# Rotate and shift as needed
		points = [pt+point.rotate(rotation) for point in points]

		# Draw
		circuit.T(points,secs=secs,trace_R=R*.75,
			trace_cap=self.params['res_cap'])

		# Set the pins
		self.L = points[0]
		self.R = points[-1]
		self.C = self.L%self.R

class Revolution:
	def __init__(self,circuit,pt,sec,norm,ang,offset=(0,0,0),axis=(0,0,1)):
		'''Constructor for revolution solid.'''
		self.circuit = circuit
		comp = circuit.component
		self.pt = Pt(*pt) if isinstance(pt,tuple) else pt
		self.sec = sec
		self.norm = Pt(*norm) if isinstance(norm,tuple) else norm
		self.ang = ang
		self.offset = Pt(*offset) if isinstance(offset,tuple) else offset
		self.axis = Pt(*axis) if isinstance(axis,tuple) else axis

		draw = sec.draw(circuit,self.pt,self.norm)
		rev = circuit.design.backend.create_revolution(comp,
			draw,self.pt+self.offset,self.axis,self.ang)

# class Text:
# 	def __init__(self,circuit,pt,text,zspan=None,size=300,**kwargs):
# 		'''Constructor for text.'''
# 		self.circuit = circuit
# 		self.pt = Pt(*pt) if isinstance(pt,tuple) else pt
# 		pt = self.pt
# 		self.text = text
# 		self.size = size
# 		self.params = circuit.params.copy()
# 		for key in kwargs: # Overwrite params with kw params
# 			if key in self.params.keys():
# 				self.params[key] = kwargs[key]
# 		self.zspan = [0, self.params['sub_H']] if zspan is None else zspan

# 		endpt = pt + (1e5,1) # Global word wrap at 10cm long
# 		texts = circuit._sketch.sketchTexts
# 		inp = texts.createInput2(text,size*circuit.design.units) # Size in cm from size in um
# 		inp.setAsMultiLine(pt.acadPoint3D,endpt.acadPoint3D,
# 			adsk.core.HorizontalAlignments.LeftHorizontalAlignment,
# 			adsk.core.VerticalAlignments.TopVerticalAlignment, 0)
# 		inp.fontName = 'Lucida Console'
# 		inp.textStyle = 5 #BoldUnderline (TBD: Doesnt work)
# 		sketch_text = texts.add(inp)
# 		if zspan[1] != 0:
# 			distup = adsk.core.ValueInput.createByReal(zspan[1]*circuit.design.units)
# 			circuit._comp.features.extrudeFeatures.addSimple(sketch_text, distup, adsk.fusion.FeatureOperations.NewBodyFeatureOperation) 
# 		if zspan[0] != 0:
# 			distdown = adsk.core.ValueInput.createByReal(zspan[0]*circuit.design.units)
# 			circuit._comp.features.extrudeFeatures.addSimple(sketch_text, distdown, adsk.fusion.FeatureOperations.NewBodyFeatureOperation) 
