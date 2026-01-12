'''
Base Design and Circuit classes.
'''

from .point import *
from .section import *
from .elements import *
from .backends import *

import math

def printm(message):
	app = adsk.core.Application.get()
	ui  = app.userInterface
	ui.messageBox(message)

class Design:
	def __init__(self,backend='fusion',origin=Pt(0,0,0),params=dict()):
		'''Construct the Design object.'''
		
		self.origin = origin # Origin wrt CAD origin
		
		# Make the params default dictionary
		self.params = { # Default values
			# Constants
			'fluid_Mu':1.01e-3, # Fluid dynamic viscosity in Pa*s
			# Fab parameters
			'slop': 250, # Slop in alignment to space elements in UM
			'sub_H': 4000, # Substrate thickness in UM
			# Element parameters
			'trace_sec': RecSec(W=250, H=50), # Default section
			'trace_R': 0, # Trace radius of curvature in UM
			'trace_cap': 'none', # Trace endcap ('none','round','square')
			'chan_sec': RecSec(W=250, H=50), # Transistor flow channel section
			'gate_sec': RecSec(W=250, H=-50), # Transistor gate section
			'res_sec': RecSec(W=50, H=50), # Resistor section
			'res_L': 1000, # Resistor bounding box length in UM
			'res_cap': 'none', # Resistor endcap ('none','round','square')
			'via_R': 350, # Via radius in UM
		}
		for key in params: # Overwrite the defaults
			self.params[key] = params[key]

		self.circuits = [] # List of all circuits

		# Set up the appropriate backend
		if backend.lower() == 'fusion':
			self.backend = FusionBackend()
		elif backend.lower() == 'freecad':
			self.backend = FreecadBackend()
		else:
			raise NotImplementedError

	def create_circuit(self,name=None,*args,**kwargs):
		'''Return a circuit to the design.'''
		# Clean the latest circuit before making new one
		if len(self.circuits)>0: self.circuits[-1].clean()
		cir = Circuit(self,name,*args,**kwargs)
		self.circuits.append(cir)
		return cir

	def clean(self):
		'''Clean all circuits in the design.'''
		if len(self.circuits) >= 1:
			for cir in self.circuits: cir.clean()

	def fuse(self):
		'''Fuse all circuits in the design.'''
		if len(self.circuits) >= 1:
			for cir in self.circuits: cir.fuse()

	def show(self):
		'''Show all circuits in the design.'''
		if len(self.circuits) >= 1:
			for cir in self.circuits: cir.show()

	def union(self,circuits):
		'''Union and fuse a list of circuits into the first circuit.'''
		# Not implemented in Fusion360
		fused = [c.fuse() for c in circuits]
		unioned = fused[0]
		for i in range(1,len(fused)):
			unioned.elements += fused[i].elements
			unioned.component = self.backend.union(unioned.component,fused[i].component)
			fused[i].delete()
		fused[0] = unioned
		return unioned

	def difference(self,stock,tool):
		'''Remove tool circuit from stock circuit in-place.'''
		# Tool circuit remains and stock circuit is modified.
		stock.fuse()
		tool.fuse()
		stock.elements += tool.elements
		stock.component = self.backend.difference(stock.component,tool.component)
		return stock

	def slice_dxf(self,zlist,filename,mirrorlist=False):
		'''Slice the 3D model, and save DXFs as filename_LXX.dxf'''
		# TBD: Only works in FreeCAD backend.
		# Go through each z, and through each circuit
		zlist = zlist if isinstance(zlist,list) else [zlist]
		mirrorlist = mirrorlist if isinstance(mirrorlist,list) else [mirrorlist]*len(zlist)
		assert len(zlist) == len(mirrorlist)
		for i in range(len(zlist)):
			filelabel = filename + f"_L{i}.dxf"
			sliced = []
			for cir in self.circuits:
				sliced += self.backend.slice_component(cir.component,zlist[i])
			self.backend.export_dxf(sliced,filelabel,mirrorlist[i])

	def draw_wafer(self,H1,H2):
		''' Helper function to draw wafer and alignment marks.'''
		cir = self.create_circuit(name='Blanks')
		W = 100 # Felix marks are ~100um
		left = self.origin + (-43750,0)
		right = self.origin + (43750,0)

		def alignmentring(cent, r1, r2, n, phase=0):
			sec1 = RecSec(W=W,H=H1,offset=(0,r1/2+r2/2,0))
			sec2 = RecSec(W=W,H=H2,offset=(0,r1/2+r2/2,0))
			for i in range(n):
				ang = i*360/n
				norm = (math.cos(ang*math.pi/180),math.sin(ang*math.pi/180),0)
				sec = sec1 if i%2==phase else sec2
				cir.rev(cent,sec,norm,-360/n)
		def alignmentline(p1, p2, phase=0):
			sec1 = RecSec(W=W/2,H=H1) # Use smaller width here
			sec2 = RecSec(W=W/2,H=H2)
			n = int((p2-p1).m//(W/2))
			for i in range(n):
				sec = sec1 if i%2==phase else sec2
				dp = (p2-p1)/n
				cir.T([p1+(i-.5)*dp,p1+(i+.5)*dp],sec)

		for c in [left, right]:
			alignmentring(c,0,W,4)
			alignmentring(c,W,2*W,16)
			alignmentring(c,2*W,3*W,16,phase=1)
			side = W*8
			alignmentline(c+(side/2,side/2),c+(side/2,-side/2))
			alignmentline(c+(side/2,-side/2),c+(-side/2,-side/2))
			alignmentline(c+(-side/2,-side/2),c+(-side/2,side/2))
			alignmentline(c+(-side/2,side/2),c+(side/2,side/2))

		mcir = self.create_circuit('Wafer')
		for side in [left, right]:
			for H in [H1,H2]:
				# Felix's window is 4200 by 2750um
				mcir.T([side+(-1500,0),side+(1500,0)],secs=RecSec(W=3000,H=H))
		windowcir = self.difference(mcir,cir)
		cir.delete()

		def waferoutline(R=52500,W=500):
			fang = 38 # Subtended angle of flat (deg)
			dang = 7 # Angle step size (deg)
			d2r = math.pi/180
			p = [self.origin+(
					R*math.cos(d2r*(-90+fang/2+i*dang)),  # noqa: E126
					R*math.sin(d2r*(-90+fang/2+i*dang)),0)
					for i in range((360-fang)//dang+1)]  # noqa: E126
			for H in [H1,H2]:
				sec = RecSec(W=W,H=H)
				mcir.T(p,sec,trace_cap='round')
				mcir.T([p[-1],p[0]],sec,trace_cap='round')

		waferoutline(51000,3000)  # 52500 to 49500 clear
		waferoutline(49000,500)  # 49250 to 48750 clear
			
class Circuit:
	def __init__(self,design,name,origin=Pt(0,0,0),**kwargs):
		'''Construct the Circuit'''
		self.design = design
		self.origin = origin
		self.name = f"Circuit{len(design.circuits)}" if name is None else name
		self.params = self.design.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]

		self.elements = [] # List of all elements

		# Create appropriate component for the design's backend
		self.component = self.design.backend.create_component()

	def clean(self):
		'''Deletes the existing sketch and creates a fresh sketch for performance improvements.'''
		self.component = self.design.backend.clean_component(self.component)

	def fuse(self):
		'''Fuse all the primitive shapes in a circuit.'''
		# Not implemented in Fusion360
		self.component = self.design.backend.fuse_component(self.component)

	def delete(self):
		'''Delete the circuit object from the design.'''
		self.design.circuits.remove(self)

	def show(self):
		'''Render and show the circuit.'''
		self.design.backend.show_component(self.component,self.name)

	## Elements
	def T(self,*args,**kwargs):
		'''Add a Trace to the circuit.'''
		trace = Trace(self,*args,**kwargs)
		self.elements.append(trace)
		return trace

	def V(self,*args,**kwargs):
		'''Add a Via to the circuit.'''
		via = Via(self,*args,**kwargs)
		self.elements.append(via)
		return via

	def M(self,*args,**kwargs):
		'''Add a Transistor to the circuit.'''
		trans = Transistor(self,*args,**kwargs)
		self.elements.append(trans)
		return trans

	def R(self,*args,**kwargs):
		'''Add a Resistor to the circuit.'''
		res = Resistor(self,*args,**kwargs)
		self.elements.append(res)
		return res

	def text(self,*args,**kwargs):
		'''Add text to the circuit.'''
		return
		txt = Text(self,*args,**kwargs)
		self.elements.append(txt)
		return txt

	def rev(self,*args,**kwargs):
		'''Add a Resistor to the circuit.'''
		rev = Revolution(self,*args,**kwargs)
		self.elements.append(rev)
		return rev
