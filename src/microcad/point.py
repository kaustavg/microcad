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

import math

class Pt:
	def __init__(self,x=0,y=0,z=0):
		'''Point constructor'''
		if isinstance(x,Pt):
			x, y, z = x.x, x.y, x.z

		self.x = x
		self.y = y
		self.z = z
		self.m = (x*x + y*y + z*z)**.5 # Length to origin

	def __str__(self):
		return str((round(self.x,2),round(self.y,2),round(self.z,2)))

	def rot(self,deg,pts):
		'''Rotate a given point or list of points around self (in XY).'''
		# Rotation units are degrees!
		isList = isinstance(pts,list)
		pts = [pts] if not isList else pts
		rotated = []
		for pt in pts:
			d = pt-self
			rads = math.pi * deg / 180
			rotated.append(self+Pt(
				d.x*math.cos(rads)-d.y*math.sin(rads),
				d.y*math.cos(rads)+d.x*math.sin(rads),
				d.z))
		return rotated[0] if not isList else rotated

	def dot(self,other):
		'''Returns the dot product of two point vectors.'''
		return self.x*other.x + self.y*other.y + self.z*other.z


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