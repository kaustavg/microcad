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

	def clean_component(self,comp,toFuse=False):
		'''In-place clean-up of a component for performance.'''
		# In fusion, can call this after drawing each element
		# Clears all existing sketches in the component and makes a fresh one
		# TBD: if toFuse is true, perform a boolean union of all objects
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
		# TBD: If a sweep starts and ends at the same point, can create degenerate geometry.
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
		'''Return a new FreeCAD component (list of Shapes).'''
		comp = []
		return comp

	def clean_component(self, comp, toFuse=False):
		'''Combine existing shapes for speed.'''
		# toFuse takes longer but fuses parts
		shapes = [c.removeSplitter() for c in comp 
		if (type(c) is self.Freecad.Part.Shape)
		or (type(c) is self.Freecad.Part.Solid)]
		if toFuse and len(shapes) > 1:
			fused = shapes[0].fuse(shapes[1:]) # Tolerance 0.0
			union = fused.removeSplitter()
			self.Freecad.Part.show(union)
			return union
		else:
			compound = self.Freecad.Part.makeCompound(shapes)
			self.Freecad.Part.show(compound)
			return compound

	def slice_component(self,comp,z):
		'''Return compound of wires formed by XY slicing at z.'''
		shape = self.Freecad.Part.Shape(self.Freecad.Part.makeCompound(comp))
		wires = shape.slice(self.pt2cad(Pt(0,0,1e3)),z*self.units)
		return wires # Return a list of wires

	def export_dxf(self,sliced,filename):
		'''Saves a list of wires as a dxf using legacy settings.'''
		import importDXF

		comp = self.Freecad.Part.Compound(sliced)
		obj = self.Freecad.App.ActiveDocument.addObject("Part::Feature","L")
		obj.Shape = comp

		# Import.writeDXFObject(objectslist, filename)
		if hasattr(importDXF, "exportOptions"):
			options = importDXF.exportOptions(filename)
			print(f"{options=}")
			importDXF.export([obj],filename, options)
		else:
			importDXF.export([obj],filename)

	## DRAWING METHODS
	def create_seg(self, comp, pt1, pt2):
		'''Return a segment between two points.'''
		# This returns a FreeCAD Edge object
		seg = self.Freecad.Part.makeLine(
			self.pt2cad(pt1),self.pt2cad(pt2))
		comp.append(seg)
		return seg

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
			print('Warning ',R,'um Fillet failed at: ',
				self.cad2pt(segfillseg[0].lastVertex().Point)/1e3,'mm.')
			seg1p1 = self.cad2pt(seg1.firstVertex().Point)
			seg1p2 = self.cad2pt(seg1.lastVertex().Point)
			seg2p1 = self.cad2pt(seg2.firstVertex().Point)
			seg2p2 = self.cad2pt(seg2.lastVertex().Point)
			print('Seg1 Len: ',(seg1p2-seg1p1).m,
				'um. Seg2 Len: ',(seg2p2-seg2p1).m,'um.')
			# print('Attempting smaller radius',R-1,'um.')
			# return self.fillet_2_segs(comp,seg1,seg2,R-1,return_endpts)
			fillet = None
		if return_endpts:
			# return seg1,fillet,seg2,\
			# 		self.cad2pt(fillet.firstVertex().Point),\
			# 		self.cad2pt(fillet.lastVertex().Point)
			return seg1,fillet,seg2,\
					self.cad2pt(seg1.lastVertex().Point),\
					self.cad2pt(seg2.firstVertex().Point)
		else:
			return seg1,fillet,seg2

	def create_path(self, comp, objs):
		'''Return a Part.Wire path from a list of objects.'''
		segs = [obj for obj in objs if obj is not None]
		try:
			path = self.Freecad.Part.Wire(segs)
		except Exception as Err:
			print('Error: Cannot create path')
			print(segs)
			for seg in segs:
				print((seg.firstVertex().Point,seg.lastVertex().Point))
			raise Err
		comp.append(path)
		# self.Freecad.Part.show(path) # TBD Remove in final for speed
		return path

	def create_sweep(self, comp, path, sec):
		'''Return a sweep from a path and one section.'''
		# If path is a FreeCAD wire, use built-in method
		face = self.Freecad.Part.Face(sec)		
		try:
			sweep = path.makePipe(face)
			comp.append(sweep)
			# self.Freecad.Part.show(sweep) 
			return sweep
		except Exception as Err:
			self.Freecad.Part.show(face)
			self.Freecad.Part.show(sec)
			self.Freecad.Part.show(path)
			print('Intersecting geometry. Likely radius too small.')
			# print('Trying loft...')
			# return self.create_loft(comp,path,[sec,sec])
		

	def create_loft(self, comp, path, secs):
		'''Return a loft from a path and multiple sections.'''
		assert len(secs) > 0
		# Use Low-level API https://dev.opencascade.org/doc/occt-7.5.0/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html
		loft_inp = self.Freecad.Part.BRepOffsetAPI.MakePipeShell(path)
		loft_inp.setTransitionMode(0)
		loft_inp.setFrenetMode(True)
		loft_inp.add(secs[0], False, True)
		loft_inp.add(secs[1], False, True)
		loft_inp.build()
		loft_inp.makeSolid()
		loft = loft_inp.shape()

		comp.append(loft)
		# self.Freecad.Part.show(loft) # Below lines may be faster since no need to recompute
		return loft
		# myObj = self.Freecad.App.ActiveDocument.addObject(
		# "Part::Feature","Loft")
		# myObj.Shape = sweep
		# return myObj

	def create_revolution(self, comp, sec, axispt, axis=Pt(0,0,1), ang=180):
		'''Return a revolved solid from a section, position, axis of rotation, and angle.'''
		face = self.Freecad.Part.Face(sec)
		solid = face.revolve(self.pt2cad(axispt),self.pt2cad(axis),ang)
		comp.append(solid)
		# self.Freecad.Part.show(solid)
		return solid