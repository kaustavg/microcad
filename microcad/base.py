'''
Base Design and Circuit classes.
'''

from .point import *
from .section import *
from .elements import *
from .backends import *

def printm(message):
	app = adsk.core.Application.get()
	ui  = app.userInterface
	ui.messageBox(message)

class Design:
	def __init__(self,backend='fusion',origin=Pt(0,0,0),params=dict()):
		'''Construct the Design object.'''
		
		self.origin = origin # Origin wrt Fusion origin
		
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

		# TODO: Clear all elements on every rerun

		# Set up the appropriate backend
		if backend.lower() == 'fusion':
			self.backend = FusionBackend()
		elif backend.lower() == 'freecad':
			self.backend = FreecadBackend()
		else:
			raise NotImplementedError


	def create_circuit(self,*args,**kwargs):
		'''Return a circuit to the design.'''
		cir = Circuit(self,*args,**kwargs)
		# Clean the latest circuit before making new one
		if len(self.circuits)>0: self.circuits[-1].clean()
		self.circuits.append(cir)
		return cir

	def clean(self):
		'''Clean the latest circuit in the design.'''
		self.circuits[-1].clean()

	def draw_substrate(self,xlen,ylen,zspan,origin=None):
		'''Draw a cuboid centered at 0,0 from z[0] to z[1].'''
		origin = self.origin if origin is None else origin
		circuit = self.add_circuit()
		left = origin + Pt(-xlen/2,0,zspan[0])
		right = origin + Pt(xlen/2,0,zspan[0])
		substrate = circuit.T([left,right],
			secs=RecSec(W=ylen,H=zspan[1]-zspan[0]))

	def slice_dxf(self,zlist,filename):
		'''Slice the 3D model, and save DXFs as filename_Lx.dxf'''
		# TBD: Only works in FreeCAD backend.

		# Go through each z, and through each circuit
		for i in range(len(zlist)):
			filelabel = filename + f"_L{i}.dxf"
			sliced = []
			for cir in self.circuits:
				sliced += self.backend.slice_component(cir.component,zlist[i])
			self.backend.export_dxf(sliced,filelabel)
			
class Circuit:
	def __init__(self,design,origin=Pt(0,0,0),**kwargs):
		'''Construct the Circuit'''
		self.design = design
		self.origin = origin

		self.params = self.design.params.copy()
		for key in kwargs: # Overwrite params with kw params
			if key in self.params.keys():
				self.params[key] = kwargs[key]

		self.elements = [] # List of all elements

		# Create appropriate component for the design's backend
		self.component = self.design.backend.create_component()

	def clean(self):
		'''Deletes the existing sketch and creates a fresh sketch for performance improvements.'''
		self.design.backend.clean_component(self.component)

	## Elements
	def T(self,*args,**kwargs):
		'''Add a Trace to the circuit.'''
		trace = Trace(self,*args,**kwargs)
		self.elements.append(trace)
		# self.clean()
		return trace

	def V(self,*args,**kwargs):
		'''Add a Via to the circuit.'''
		via = Via(self,*args,**kwargs)
		self.elements.append(via)
		# self.clean()
		return via

	def M(self,*args,**kwargs):
		'''Add a Transistor to the circuit.'''
		trans = Transistor(self,*args,**kwargs)
		self.elements.append(trans)
		# self.clean()
		return trans

	def R(self,*args,**kwargs):
		'''Add a Resistor to the circuit.'''
		res = Resistor(self,*args,**kwargs)
		self.elements.append(res)
		# self.clean()
		return res

	def text(self,*args,**kwargs):
		'''Add text to the circuit.'''
		return
		txt = Text(self,*args,**kwargs)
		self.elements.append(txt)
		# self.clean()
		return txt

	def rev(self,*args,**kwargs):
		'''Add a Resistor to the circuit.'''
		rev = Revolution(self,*args,**kwargs)
		self.elements.append(rev)
		# self.clean()
		return rev