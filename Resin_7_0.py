#Author-Kaustav Gopinathan
#Description-Resin Test Chip


'''
Resin_7_0

Draw two transistors for the op-amp.
Have both halves printed simultaneously.
Transistor sizes are 27*9=243um.
Height is 50um (to prevent membrane collapse).
Make bus lines deep (200um).

'''

import sys
sys.path.append(r'C:\Users\Kaustav\Documents\Python\microcad')
import microcad as mc


# Script to draw everything
def main():
	# Create a microcad CAD drawing
	design = mc.Design() # Units are such that 1mm in drawing = 1mm

	xstage = 51.64e3 # x size
	ystage = 29.05e3 # y size
	ut = 0.5 * (xstage/1920 + ystage/1080) # 26.89700um

	xstage = 12e3
	ystage = 10e3
	eps = 1e-3

	# This is a two layer design with several sections (due to tapers)
	cir = design.add_circuit()

	Ws = [ut*9, ut*9]
	via_H =4000 # Thickness of resin substrate
	cir.params['via_H'] = via_H
	H = 50 # Trace and transistor height
	bus_H = 200 # um Bus trace height
	cir.params['trans_H'] = H
	slop = 100 # Slop around transistors
	cir.params['slop'] = slop # Alignment slop
	cir.params['via_R'] = 350 # Radius of via through-holes
	# 1587um = 1/16" diameter tubing
	# Add a moat around pin holes to allow membrane coring distortion
	moat_R = 1000
	moat_H = 50
	
	# Do two sets of traces on top and bottom
	lo = lambda w: mc.RectSect(W=w,H=-H)
	hi = lambda w: mc.RectSect(W=w,H=H)
	buslo = lambda w: mc.RectSect(W=w,H=-bus_H)
	bushi = lambda w: mc.RectSect(W=w,H=bus_H)

	# p1 = cir.origin + (1000,0)
	# p2 = p1 + (500,-1000,0)
	# cir.T([cir.origin,p1,p2])


	# Ports (in LRUD order)
	dx = xstage/2
	dy = ystage/4
	g1 = cir.P((-1.0*dx,0,0),zspan=[0,-via_H],anchor='C')
	g2 = cir.P((1.0*dx,0,0),zspan=[0,-via_H],anchor='C')
	p1 = cir.P((-.5*dx,1.5*dy,0),anchor='C')
	p2 = cir.P((0.5*dx,1.5*dy,0),anchor='C')
	p3 = cir.P((-.5*dx,-1.5*dy,0),anchor='C')
	p4 = cir.P((0.5*dx,-1.5*dy,0),anchor='C')

	# Transistors spaced 1mm apart center-to-center
	space = 500
	m1pt = cir.origin+(-space,0,0)
	m2pt = cir.origin+(space,0,0)
	# m1 = cir.M((-space,0,0),anchor='C',trans_L=Ws[0],trans_W=Ws[0])
	# m2 = cir.M((space,0,0),anchor='C',trans_L=Ws[1],trans_W=Ws[1])

	# Connect everthing up without transistor objects
	cir.T([g1.C,(-1500,0)],secs=buslo(Ws[0]))
	cir.T([g2.C,(1500,0)],secs=buslo(Ws[1]))
	cir.T([(-1500,0),(1500,0)],secs=lo(Ws[0]))
	# cir.T([g1.C,(-2250,0),(-1500,0),(-100,0),
	# 	(100,0),(1500,0),(2250,0),g2.C],
	# 	secs=[buslo(Ws[0]),buslo(Ws[0]),lo(Ws[0]),lo(Ws[0]),
	# 	lo(Ws[1]),lo(Ws[1]),buslo(Ws[1]),buslo(Ws[1])])
	space = 1.75e3
	cir.T([p1.C,m1pt+(0,space),m1pt+(0,space-750)],
		secs=[bushi(Ws[0]),bushi(Ws[0]),bushi(Ws[0])],trace_R=250)
	cir.T([m1pt+(0,space-750),m1pt-(0,space-750)],
		secs=[hi(Ws[0]),hi(Ws[0]),hi(Ws[0])],trace_R=250)
	cir.T([m1pt-(0,space-750),m1pt-(0,space),p3.C],
		secs=[bushi(Ws[0]),bushi(Ws[0]),bushi(Ws[0])],trace_R=250)
	cir.T([p2.C,m2pt+(0,space),m2pt+(0,space-750)],
		secs=[bushi(Ws[0]),bushi(Ws[0]),bushi(Ws[0])],trace_R=250)
	cir.T([m2pt+(0,space-750),m2pt-(0,space-750)],
		secs=[hi(Ws[0]),hi(Ws[0]),hi(Ws[0])],trace_R=250)
	cir.T([m2pt-(0,space-750),m2pt-(0,space),p4.C],
		secs=[bushi(Ws[0]),bushi(Ws[0]),bushi(Ws[0])],trace_R=250)

	# Connect everything up
	# cir.T([g1.C,m1.S],secs=lo(Ws[0]))
	# cir.T([m1.D,(-100,0),(100,0),m2.S],secs=[lo(Ws[0]),lo(Ws[0]),lo(Ws[1]),lo(Ws[1])])
	# cir.T([m2.D,g2.C],secs=lo(Ws[1]))
	# space = 2e3
	# cir.T([p1.C,m1.G2+(0,space),m1.G2],secs=hi(Ws[0]))
	# cir.T([m1.G1,m1.G1-(0,space),p3.C],secs=hi(Ws[0]))
	# cir.T([p2.C,m2.G2+(0,space),m2.G2],secs=hi(Ws[1]))
	# cir.T([m2.G1,m2.G1-(0,space),p4.C],secs=hi(Ws[1]))

	# Draw alignment holes
	ali_R = 1270/2
	cir.V((10e3,10e3),zspan=[-via_H,via_H],anchor='C',via_R=ali_R)
	cir.V((10e3,-10e3),zspan=[-via_H,via_H],anchor='C',via_R=ali_R)
	cir.V((-10e3,-10e3),zspan=[-via_H,via_H],anchor='C',via_R=ali_R)
	cir.V((10e3,10e3),zspan=[-moat_H,moat_H],anchor='C',via_R=moat_R)
	cir.V((10e3,-10e3),zspan=[-moat_H,moat_H],anchor='C',via_R=moat_R)
	cir.V((-10e3,-10e3),zspan=[-moat_H,moat_H],anchor='C',via_R=moat_R)

	# Draw substrate
	xsub = 25e3
	ysub = 28e3
	design.draw_substrate(xsub,ysub,[eps,via_H-eps])
	design.draw_substrate(xsub,ysub,[eps-via_H,-eps])