'''
Backends for various CAD drawing programs.

The backend object is an attribute of the design object. When the design object is created, a backend must be specified. The appropriate backend object is then created and initialized. All relevant backend-specific references (like sketches, components, etc.) are attributes of the backend object.

Each backend must support the following operations:

- initialize itself and import relevant modules
- add a component (circuit)
- clean component (can be run after an element has been drawn for performance)

- add edge
- fillet existing vertex between edges
- make path
- loft using path and multiple sections
- draw cylinder (can be re-written as tube loft)
- draw port (can be re-written in tube lofts)
- draw thick text

- convert point to CAD point
- convert CAD point to point


'''

from .point import *

import math

class CADBackend:
	pass

class FusionBackend(CADBackend):
	# Import Fusion API modules
	import adsk.core, adsk.fusion, traceback
	
	def __init__(self):
		'''Fusion 360 backend constructor'''
		self.name = 'fusion'
		self.units = 1e-4 # Number of CAD units (cm for fusion) in one Point unit (um)

		self._app = FusionBackend.adsk.core.Application.get()
		self._ui = self._app.userInterface
		self._product = self._app.activeProduct
		self._design = FusionBackend.adsk.fusion.Design.cast(self._product)
		# Do not capture design history for speed
		self._design.designType = FusionBackend.adsk.fusion.DesignTypes.DirectDesignType
		self._root_comp = self._design.rootComponent

	def pt2cad(self,pt):
		'''Return the appropriate CAD point for the given Point object.'''
		return FusionBackend.adsk.core.Point3D.create(
			float(pt.x*self.units),float(pt.y*self.units),float(pt.z*self.units))
	def cad2pt(self,cadpt):
		'''Return a Point object for a CAD point.'''
		return Pt(cadpt.x/self.units,cadpt.y/self.units,cadpt.z/self.units)

	def create_component(self):
		'''Return a new Fusion component including sketchplane (for a new circuit).'''
		occ = self._root_comp.occurrences.addNewComponent(FusionBackend.adsk.core.Matrix3D.create())
		comp = occ.component
		self.clean_component(comp)
		return comp

	def clean_component(self,comp):
		'''In-place clean-up of a component for performance.'''
		# In fusion, can call this after drawing each element
		# Clears all existing sketches in the component and makes a fresh one
		for i in comp.sketches.count:
			sketch = comp.sketches.item(i)
			sketch.deleteMe()
		sketch = comp.sketches.add(comp.xYConstructionPlane)
		sketch.isComputeDeferred = True # Saves time evaluating
		sketch.areProfilesShown = False # Saves time drawing
		sketch.isLightBulbOn = False # Reduce visual clutter

	## DRAWING METHODS
	def create_seg(self,comp,pt1,pt2):
		'''Return a Fusion sketchline by two points.'''
		sketch = comp.sketches.item(0) # Get the sketch of the component
		sketchline = sketch.sketchCurves.sketchLines.addByTwoPoints(self.pt2cad(pt1),self.pt2cad(pt2))
		return sketchline

	def fillet_2_segs(self,comp,seg1,seg2,R,return_endpts=False):
		'''Create a fillet between two sketchlines (modifying them) and return the sketcharc. Optionally return endpts of arc.'''
		sketch = comp.sketches.item(0) # Get the sketch of the component
		sketcharc = sketch.sketchCurves.sketchArcs.addFillet(
					seg1, seg1.endSketchPoint.geometry,
					seg2, seg2.startSketchPoint.geometry,
					abs(R)*self.units)
		if return_endpts:
			return sketcharc,\
				self.cad2pt(seg1.endSketchPoint.geometry),\
				self.cad2pt(seg2.startSketchPoint.geometry)
		else:
			return sketcharc

	def create_path(self,comp,objs):
		'''Return a path made from list of sketchlines and sketcharcs.'''
		collection = FusionBackend.adsk.core.ObjectCollection.create()
		for obj in objs:
			if obj.isValid:
				collection.add(obj)
		path = comp.features.createPath(collection)
		return path

	def create_loft(self,comp,path,secs):
		'''Return a loft from a path and multiple sections.'''
		# Maybe you don't need to create a new object collection here?
		loft_inp = self.comp.features.loftFeatures.createInput(
			FusionBackend.adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
		# Add sections
		for sec in secs:
			loft_inp.loftSections.add(sec)
		# Add center line
		loft_inp.centerLineOrRails.addCenterLine(path)
		loft_inp.isSolid = True
		loft = comp.features.loftFeatures.add(loft_inp)
		return loft