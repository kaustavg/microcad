'''
Point Class.

Overloaded operations:
+ : Add in x, y, and z
- : Subtract in x, y, and z
| : Take x of left point and y of right point
^ : Take x,y of left point and z of right point
% : Return midpoint in x and y
* : Multiply elementwise by a scalar
/ : Divide elementwise by a scalar

All operations work on tuples as well.

'''

import adsk.core, adsk.fusion, traceback
import math

class Pt:
	def __init__(self,x=0,y=0,z=0):
		'''Point constructor'''

		# Note that Fusion only works in cm
		# If units=.1 then 1mm in fusion -> 1um
		# If units=1e-4 then 1um in fusion -> 1um
		self.units = 1e-4 # Number of cm in 1 unit
		units = self.units 

		# If first argument is an acadPoint3D, then convert it
		if isinstance(x,adsk.core.Point3D):
			z = x.z/units
			y = x.y/units
			x = x.x/units

		self.x = x
		self.y = y
		self.z = z
		self.m = (x*x + y*y + z*z)**.5 # Length to origin

		self.acadPoint3D = adsk.core.Point3D.create(
			float(x*units),float(y*units),float(z*units))

	def __str__(self):
		return str((self.x,self.y,self.z))

	def rotate(self,degrees,center=(0,0,0)):
		'''Returns a rotated point in 2D around a center.'''
		# Rotation units are degrees!
		d = self-center
		rads = math.pi * degrees / 180
		return center+Pt(
			d.x*math.cos(rads)-d.y*math.sin(rads),
			d.y*math.cos(rads)+d.x*math.sin(rads),
			d.z)


	# Overloaded operators
	def __or__(self,other):
		'''Take the x of the self and the y of other.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(self.x,other.y)

	def __ror__(self,other):
		'''Take the x of other and the y of self.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(other.x,self.y)

	def __mod__(self,other):
		'''Take the midpoint of the two points.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt((self.x+other.x)/2,(self.y+other.y)/2)

	def __rmod__(self,other):
		'''Called when python tries to evaluate other % self.'''
		return self % other

	def __xor__(self,other):
		'''Take the x,y of self and the z of other.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(self.x,self.y,other.z)

	def __rxor__(self,other):
		'''Called when python tries to evaluate other ^ self.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(other.x,other.y,self.z)

	def __add__(self,other):
		'''Sum the x and y.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(self.x+other.x,self.y+other.y,self.z+other.z)

	def __radd__(self,other):
		'''Called when python tries to evaluate other + self.'''
		return self + other

	def __sub__(self,other):
		'''Difference the x and y.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(self.x-other.x,self.y-other.y,self.z-other.z)
	def __rsub__(self,other):
		'''Called when python tries to evaluate other - self.'''
		if not isinstance(other,Pt):
			other = Pt(*other)
		return Pt(other.x-self.x,other.y-self.y,other.z-self.z)

	def __mul__(self,scalar):
		'''Multiply with scalar.'''
		return Pt(self.x*scalar,self.y*scalar,self.z*scalar)
	def __rmul__(self,other):
		'''Called when python tries to evaluate other * self.'''
		return self * other

	def __truediv__(self,scalar):
		'''Divide by scalar.'''
		return self * (1/scalar)