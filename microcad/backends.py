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
	def __init__(self):
		'''Fusion 360 backend constructor'''
		self.name = 'fusion'
		self.units = 1e-4 # Number of CAD units (cm for fusion) in one Point unit (um)

		# Import Fusion API modules
		import adsk.core as coreModule
		import adsk.fusion as fusionModule
		self.adsk = lambda: None # Cursed way to make generic object
		self.adsk.core = coreModule
		self.adsk.fusion = fusionModule

		# Set up Fusion environment
		self._app = self.adsk.core.Application.get()
		self._ui = self._app.userInterface
		self._product = self._app.activeProduct
		self._design = self.adsk.fusion.Design.cast(self._product)
		# Do not capture design history for speed
		self._design.designType = self.adsk.fusion.DesignTypes.DirectDesignType
		self._root_comp = self._design.rootComponent

	def pt2cad(self,pt):
		'''Return the CAD point for the given Point object.'''
		return self.adsk.core.Point3D.create(
			float(pt.x*self.units),float(pt.y*self.units),float(pt.z*self.units))
	def cad2pt(self,cadpt):
		'''Return a Point object for a CAD point.'''
		return Pt(cadpt.x/self.units,cadpt.y/self.units,cadpt.z/self.units)

	def create_component(self):
		'''Return a new Fusion component including sketchplane (for a new circuit).'''
		occ = self._root_comp.occurrences.addNewComponent(self.adsk.core.Matrix3D.create())
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
		'''Create a fillet between two sketchlines and return sketchline, sketcharc, sketchline. Optionally return endpts of arc.'''
		sketch = comp.sketches.item(0) # Get the sketch of the component
		# If a seg is too short, filleting may delete it. In that case, store the other side of the seg and return that.
		sketcharc = sketch.sketchCurves.sketchArcs.addFillet(
					seg1, seg1.endSketchPoint.geometry,
					seg2, seg2.startSketchPoint.geometry,
					abs(R)*self.units)
		if return_endpts:
			return seg1,sketcharc,seg2,\
				self.cad2pt(seg1.endSketchPoint.geometry),\
				self.cad2pt(seg2.startSketchPoint.geometry)
		else:
			return seg1,sketcharc,seg2

	def create_path(self,comp,objs):
		'''Return a path made from list of sketchlines and sketcharcs.'''
		assert len(objs) > 0
		collection = self.adsk.core.ObjectCollection.create()
		for obj in objs:
			if obj.isValid:
				collection.add(obj)
		path = comp.features.createPath(collection)
		return path

	def create_sweep(self,comp,path,sec):
		'''Return a sweep from a path and one section.'''
		sweep_inp = comp.features.sweepFeatures.createInput(
			sec,path,self.adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
		# raise Exception(path.count)
		sweep = comp.features.sweepFeatures.add(sweep_inp)
		return sweep

	def create_loft(self,comp,path,secs):
		'''Return a loft from a path and multiple sections.'''
		assert len(secs) > 0
		loft_inp = comp.features.loftFeatures.createInput(
			self.adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
		# Add sections
		for sec in secs:
			loft_inp.loftSections.add(sec)
		# Add center line
		loft_inp.centerLineOrRails.addCenterLine(path)
		loft_inp.isSolid = True
		# loft_inp.isTangentEdgesMerged = False
		# loft_inp.startLoftEdgeAlignment = self.adsk.fusion.LoftEdgeAlignments.AlignToSurfaceLoftEdgeAlignment;
		# loft_inp.endLoftEdgeAlignment = self.adsk.fusion.LoftEdgeAlignments.AlignToSurfaceLoftEdgeAlignment;
		loft = comp.features.loftFeatures.add(loft_inp)
		return loft

class FreecadBackend(CADBackend):
	def __init__(self):
		'''FreeCAD backend constructor'''
		self.name = 'freecad'
		self.units = 1e-3 # Number of CAD units (mm for freecad) in one Point unit (um)

		# Import Freecad API modules
		import FreeCAD as AppModule
		import Part as PartModule
		import DraftGeomUtils as DraftGeomUtilsModule
		self.Freecad = lambda: None # Cursed way to make generic object
		self.Freecad.App = AppModule
		self.Freecad.Part = PartModule
		self.Freecad.DraftGeomUtils = DraftGeomUtilsModule

		# Set up Freecad environment
		self._doc = self.Freecad.App.ActiveDocument
		if self._doc is None:
			self._doc = self.Freecad.App.newDocument("Microcad Script")
		# self._root_comp = self._doc.addObject('Part::Feature', 'Component')
		# self.clean_component(self._root_comp)

	def pt2cad(self, pt):
		'''Return the Freecad vector for the given Point object.'''
		return self.Freecad.App.Vector(
			float(pt.x * self.units),
			float(pt.y * self.units),
			float(pt.z * self.units))

	def cad2pt(self, cadpt):
		'''Return a Point object for a FreeCAD vector.'''
		return Pt(cadpt.x/self.units,cadpt.y/self.units,cadpt.z/self.units)

	def create_component(self):
		'''Return a new FreeCAD component (Part Feature).'''
		comp = self._doc.addObject('Part::Feature', 'Component')
		# self.clean_component(comp)
		return comp

	def clean_component(self, comp):
		'''Remove existing sketches and create a new sketch.'''
		pass

	## DRAWING METHODS
	def create_seg(self, comp, pt1, pt2):
		'''Return a segment between two points.'''
		# This returns a FreeCAD Edge object
		return self.Freecad.Part.makeLine(
			self.pt2cad(pt1),self.pt2cad(pt2))

	def fillet_2_segs(self, comp, seg1, seg2, R, return_endpts=False):
		'''Create a fillet between two lines and return seg, arc, seg. Optionally return endpts of arc.'''
		# DraftGeomUtils.fillet is a low-level function that takes two edges
		# and returns [newedge, fillet, newedge]
		segfillseg = self.Freecad.DraftGeomUtils.fillet(
			[seg1,seg2],abs(R)*self.units,chamfer=False)
		seg1 = segfillseg[0]
		seg2 = segfillseg[-1]
		if len(segfillseg) == 3:
			fillet = segfillseg[1]
		else:
			print('Warning: Fillet failed at')
			print(self.cad2pt(segfillseg[0].lastVertex().Point))
			fillet = None
		if return_endpts:
			return seg1,fillet,seg2,\
					self.cad2pt(fillet.firstVertex().Point),\
					self.cad2pt(fillet.lastVertex().Point)
		else:
			return seg1,fillet,seg2

	def create_path(self, comp, objs):
		'''Return a Part.Wire path from a list of objects.'''
		segs = [obj for obj in objs if obj is not None]
		try:
			path = self.Freecad.Part.Wire(segs)
		except Exception as Err:
			print('Cannot create path')
			print(segs)
			for seg in segs:
				print((seg.firstVertex().Point,seg.lastVertex().Point))
			raise Err
		# self.Freecad.Part.show(path)
		return path

	def create_sweep(self, comp, path, sec):
		'''Return a sweep from a path and one section.'''
		# If path is a FreeCAD wire, use built-in method
		print('Creating sweep')
		face = self.Freecad.Part.Face(sec)		
		try:
			sweep = path.makePipe(face)
		except Exception as Err:
			self.Freecad.Part.show(face)
			self.Freecad.Part.show(sec)
			self.Freecad.Part.show(path)
			print('Intersecting geometry. Likely radius too small.')
			raise Err
		self.Freecad.Part.show(sweep) 
		return sweep

	def create_loft(self, comp, path, secs):
		'''Return a loft from a path and multiple sections.'''
		assert len(secs) > 0
		# Use Low-level API https://dev.opencascade.org/doc/occt-7.5.0/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html
		loft_inp = self.Freecad.Part.BRepOffsetAPI.MakePipeShell(path)
		loft_inp.setTransitionMode(0)
		loft_inp.setFrenetMode(True)
		loft_inp.add(secs[0], True, True)
		loft_inp.add(secs[1], True, True)
		loft_inp.build()
		loft_inp.makeSolid()
		loft = loft_inp.shape()

		self.Freecad.Part.show(loft) # Below lines may be faster since no need to recompute
		return loft
		# myObj = self.Freecad.App.ActiveDocument.addObject(
		# "Part::Feature","Loft")
		# myObj.Shape = sweep
		# return myObj