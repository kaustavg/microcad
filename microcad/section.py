'''
Section classes.
'''

import adsk.core, adsk.fusion, traceback

import math

from .point import *


class Section:
	# TBD: Implement a method called "invert" to return a new section with 
	# inverted height in Z. Currently, we just copy the section and rewrite the 
	# value for Section.H to -Section.H
	pass

class RecSec(Section):
	def __init__(self,W=250, H=50):
		'''Constructor for Rectangular Section.'''
		self.W = W
		self.H = H
		self.span = W # Used to avoid loft self-intersections
		h = abs(H*1e-6) # SI height
		w = abs(W*1e-6) # SI width
		# Multiply following by mu*L to obtain resistance in SI
		# This has units of 1/(m^4)
		self.res_muL = 12/((1-0.63*(h/w))*h**3*w)

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		W = self.W
		H = self.H
		px = [0,0,0,0]
		py = [-W/2,W/2,W/2,-W/2]
		pz = [0,0,H,H]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point
		# Draw in fusion
		collection = adsk.core.ObjectCollection.create()
		for i in range(len(pts)):
			collection.add(circuit._sketch.sketchCurves.sketchLines
				.addByTwoPoints(pts[i-1].acadPoint3D,pts[i].acadPoint3D))
		path = circuit._comp.features.createPath(collection)
		return path

class CurveSec(Section):
	def __init__(self,W=250,H=50,R=None):
		'''Constructor for a Curvilinear section.'''
		self.W = W
		self.H = H
		self.R = H if R is None else R
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
		W = self.W
		H = self.H
		R = self.R
		px = [0,0,0,0]
		py = [-W/2,W/2,W/2,-W/2]
		pz = [0,0,H,H]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point
		# Draw in fusion
		segs = []
		for i in range(len(pts)):
			seg = circuit._sketch.sketchCurves.sketchLines.addByTwoPoints(
				pts[i-1].acadPoint3D,pts[i].acadPoint3D)
			segs.append(seg)
		# Add fillets
		arc1 = circuit._sketch.sketchCurves.sketchArcs.addFillet(
			segs[2],segs[2].endSketchPoint.geometry,
			segs[3],segs[3].startSketchPoint.geometry,
			abs(R)*circuit.design.units)
		arc2 = circuit._sketch.sketchCurves.sketchArcs.addFillet(
			segs[-1],segs[-1].endSketchPoint.geometry,
			segs[0],segs[0].startSketchPoint.geometry,
			abs(R)*circuit.design.units)
		collection = adsk.core.ObjectCollection.create()
		objs = segs[:3]+[arc1]+[segs[3]]+[arc2] # Add in order
		for obj in objs:
			if obj.isValid:
				collection.add(obj)
		path = circuit._comp.features.createPath(collection)
		return path

class TrapzSec(Section):
	def __init__(self,W=250, H=50, Wt=None, Ht=None):
		'''Constructor for Trapezoidal Section.'''
		self.W = W
		self.H = H
		# Height and Width of tapered section is Ht and Wt
		self.Wt = W-2*abs(H) if Wt is None else Wt
		self.Ht = math.copysign((W-self.Wt)/2,H) if Ht is None else Ht 
		self.span = W # Used to avoid loft self-intersections

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		W = self.W
		H = self.H
		Wt = self.Wt
		Ht = self.Ht
		dW = (W-Wt)/2 # half Width difference
		px = [0,0,0,0,0,0]
		py = [-W/2+dW,W/2-dW,W/2,W/2,-W/2,-W/2]
		pz = [H,H,H-Ht,0,0,H-Ht]
		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point
		# Draw in fusion
		collection = adsk.core.ObjectCollection.create()
		for i in range(len(pts)):
			if (pts[i-1]-pts[i]).m > 1e-3:
				collection.add(circuit._sketch.sketchCurves.sketchLines
					.addByTwoPoints(pts[i-1].acadPoint3D,pts[i].acadPoint3D))
		path = circuit._comp.features.createPath(collection)
		return path

class TubeSec(Section):
	def __init__(self,R=250):
		'''Constructor for a Tube section.'''
		self.R = R
		self.span = 2*R # Used to avoid loft self-intersections

	def draw(self,circuit,pc,n):
		'''Return the path centered around pc normal to n.'''
		# Here we draw the section normal to x axis, then rotate it.
		m = 32 # Number of facets to make up the tube
		R = self.R

		px = [0 for i in range(m)];
		py = [R*math.cos(2*math.pi*i/m) for i in range(m)]
		pz = [R*math.sin(2*math.pi*i/m) for i in range(m)]

		# Rotate the x and y
		u = n/n.m
		rotm = [[u.x,-u.y],[u.y,u.x]]
		rotx = [rotm[0][0]*px[i]+rotm[0][1]*py[i] for i in range(len(px))]
		roty = [rotm[1][0]*px[i]+rotm[1][1]*py[i] for i in range(len(py))]
		pts = [Pt(rotx[i],roty[i],pz[i]) for i in range(len(px))]
		pts = [pt+pc for pt in pts] # Offset by center point
		# Draw in fusion
		collection = adsk.core.ObjectCollection.create()
		for i in range(len(pts)):
			collection.add(circuit._sketch.sketchCurves.sketchLines
				.addByTwoPoints(pts[i-1].acadPoint3D,pts[i].acadPoint3D))
		path = circuit._comp.features.createPath(collection)
		return path