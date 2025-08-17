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
		'''Return the CAD point for the given Point object.'''
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
		for i in range(comp.sketches.count):
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
		# If a seg is too short, filleting may delete it. In that case, store the other side of the seg and return that.
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
		assert len(objs) > 0
		collection = FusionBackend.adsk.core.ObjectCollection.create()
		for obj in objs:
			if obj.isValid:
				collection.add(obj)
		path = comp.features.createPath(collection)
		return path

	def create_sweep(self,comp,path,sec):
		'''Return a sweep from a path and one section.'''
		sweep_inp = comp.features.sweepFeatures.createInput(
			sec,path,FusionBackend.adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
		# raise Exception(path.count)
		sweep = comp.features.sweepFeatures.add(sweep_inp)
		return sweep

	def create_loft(self,comp,path,secs):
		'''Return a loft from a path and multiple sections.'''
		assert len(secs) > 0
		loft_inp = comp.features.loftFeatures.createInput(
			FusionBackend.adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
		# Add sections
		for sec in secs:
			loft_inp.loftSections.add(sec)
		# Add center line
		loft_inp.centerLineOrRails.addCenterLine(path)
		loft_inp.isSolid = True
		# loft_inp.isTangentEdgesMerged = False
		# loft_inp.startLoftEdgeAlignment = FusionBackend.adsk.fusion.LoftEdgeAlignments.AlignToSurfaceLoftEdgeAlignment;
		# loft_inp.endLoftEdgeAlignment = FusionBackend.adsk.fusion.LoftEdgeAlignments.AlignToSurfaceLoftEdgeAlignment;
		loft = comp.features.loftFeatures.add(loft_inp)
		return loft

class FreecadBackend(CADBackend):
	# Import FreeCAD API modules
	import FreeCAD as App
	import FreeCADGui as Gui
	import Part, Draft

	def __init__(self):
		'''FreeCAD backend constructor'''
		self.name = 'freecad'
		self.units = 1e-3 # Number of CAD units (mm for freecad) in one Point unit (um)

		self._doc = FreecadBackend.App.ActiveDocument
		if self._doc is None:
			self._doc = FreecadBackend.App.newDocument()
		self._root_comp = self._doc.addObject('Part::Feature', 'Component')
		self.clean_component(self._root_comp)

	def pt2cad(self, pt):
		'''Return the Freecad vector for the given Point object.'''
		return FreecadBackend.App.Vector(
			float(pt.x * self.units),
			float(pt.y * self.units),
			float(pt.z * self.units))

	def cad2pt(self, cadpt):
		'''Return a Point object for a FreeCAD vector.'''
		return Pt(cadpt.x/self.units,cadpt.y/self.units,cadpt.z/self.units)

	def create_component(self):
		'''Return a new FreeCAD component (Part Feature).'''
		comp = self._doc.addObject('Part::Feature', 'Component')
		self.clean_component(comp)
		return comp

	def clean_component(self, comp):
		'''Remove existing sketches and create a new sketch.'''
		if hasattr(comp, 'Group'):
			for obj in list(comp.Group):
				self._doc.removeObject(obj.Name)
		sketch = self._doc.addObject('Sketcher::SketchObject', 'Sketch')
		comp.addObject(sketch)
		self._doc.recompute()

	## DRAWING METHODS
	def create_seg(self, comp, pt1, pt2):
		'''Return a Draft line between two points.'''
		return FreecadBackend.Draft.makeLine(self.pt2cad(pt1), self.pt2cad(pt2))

	def fillet_2_segs(self, comp, seg1, seg2, R, return_endpts=False):
		'''Create a fillet between two Draft lines and return the resulting arc.'''
		fillet = FreecadBackend.Draft.fillet([seg1, seg2], R * self.units)
		if return_endpts:
			return (fillet,
					self.cad2pt(seg1.Shape.EndPoint),
					self.cad2pt(seg2.Shape.StartPoint))
		else:
			return fillet

	def create_path(self, comp, objs):
		'''Return a Part.Wire path from a list of objects.'''
		edges = []
		for obj in objs:
			shape = obj.Shape if hasattr(obj, 'Shape') else obj
			edges.extend(shape.Edges)
		path = FreecadBackend.Part.Wire(edges)
		return path

	def create_sweep(self, comp, path, sec):
		'''Return a sweep from a path and one section.'''
		sweep = comp.newObject('Part::Sweep', 'Sweep')
		sweep.Sections = [sec]
		sweep.Spine = path
		sweep.Solid = True
		self._doc.recompute()
		return sweep

	def create_loft(self, comp, path, secs):
		'''Return a loft from a path and multiple sections.'''
		loft = comp.newObject('Part::Loft', 'Loft')
		loft.Sections = secs
		loft.Solid = True
		loft.Ruled = False
		loft.Closed = False
		loft.addObject(path)
		self._doc.recompute()
		return loft