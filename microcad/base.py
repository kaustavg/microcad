'''
Base Design and Circuit classes.
'''

import adsk.core, adsk.fusion, traceback

from .point import *
from .section import *
from .elements import *

def printm(message):
	app = adsk.core.Application.get()
	ui  = app.userInterface
	ui.messageBox(message)

class Design:
	def __init__(self,origin=Pt(0,0,0),params=dict()):
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
			'trace_R': 250, # Trace radius of curvature in UM
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

		self.units = Pt().units # Get units from Point class

		self.circuits = [] # List of all circuits

		# TBD: Clear all elements on every rerun

		# Set up the app
		self._app = adsk.core.Application.get()
		self._ui = self._app.userInterface
		self._product = self._app.activeProduct
		self._design = adsk.fusion.Design.cast(self._product)
		# Do not capture design history for speed
		self._design.designType = adsk.fusion.DesignTypes.DirectDesignType
		self._root_comp = self._design.rootComponent

	def add_circuit(self,*args,**kwargs):
		'''Add a circuit to the design.'''
		cir = Circuit(self,*args,**kwargs)
		self.circuits.append(cir)
		return cir

	def draw_substrate(self,xlen,ylen,zspan,origin=None):
		'''Draw a cuboid centered at 0,0 from z[0] to z[1].'''
		origin = self.origin if origin is None else origin
		circuit = self.add_circuit()
		left = origin + Pt(-xlen/2,0,zspan[0])
		right = origin + Pt(xlen/2,0,zspan[0])
		substrate = circuit.T([left,right],
			secs=RecSec(W=ylen,H=zspan[1]-zspan[0]))
		# Perform intersection with 

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

		# Create the circuit component and sketchplane
		self._occ = self.design._root_comp.occurrences.addNewComponent(
			adsk.core.Matrix3D.create())
		self._comp = self._occ.component
		self._sketch = self._comp.sketches.add(
			self._comp.xYConstructionPlane)
		self._sketch.isComputeDeferred = True # Saves time evaluating
		self._sketch.areProfilesShown = False # Saves time drawing
		self._sketch.isLightBulbOn = False # Reduce visual clutter

	def clean_sketch(self):
		'''Deletes the existing sketch and creates a fresh sketch for performance improvements.'''
		# Fusion becomes much slower the more objects you add to a sketch
		# Run each time after finished drawing a new element
		self._sketch.deleteMe()
		self._sketch = self._comp.sketches.add(
			self._comp.xYConstructionPlane)
		self._sketch.isComputeDeferred = True # Saves time evaluating
		self._sketch.areProfilesShown = False # Saves time drawing
		self._sketch.isLightBulbOn = False # Reduce visual clutter

	## Elements
	def T(self,*args,**kwargs):
		'''Add a Trace to the circuit.'''
		trace = Trace(self,*args,**kwargs)
		self.elements.append(trace)
		self.clean_sketch()
		return trace

	def V(self,*args,**kwargs):
		'''Add a Via to the circuit.'''
		via = Via(self,*args,**kwargs)
		self.elements.append(via)
		self.clean_sketch()
		return via

	def M(self,*args,**kwargs):
		'''Add a Transistor to the circuit.'''
		trans = Transistor(self,*args,**kwargs)
		self.elements.append(trans)
		self.clean_sketch()
		return trans

	def R(self,*args,**kwargs):
		'''Add a Resistor to the circuit.'''
		res = Resistor(self,*args,**kwargs)
		self.elements.append(res)
		self.clean_sketch()
		return res

	def P(self,*args,**kwargs):
		'''Add a Port to the circuit.'''
		port = Port(self,*args,**kwargs)
		self.elements.append(port)
		self.clean_sketch()
		return port

	def text(self,*args,**kwargs):
		'''Add text to the circuit.'''
		txt = Text(self,*args,**kwargs)
		self.elements.append(txt)
		self.clean_sketch()
		return txt