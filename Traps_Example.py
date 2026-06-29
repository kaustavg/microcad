import microcad as mc

def trap(cir, start):
	''' Draws one cell trap'''

	H = 25 # Channel height
	W = 200 # Large trace width
	w = 5 # Orifice width
	l = 300# 10 # Length after orifice
	R = 25 # Radius of cell trap
	Ws = 500 # Switch width
	slop = 250

	# Sections
	chansec = mc.RecSec(W=W,H=H) # Channel section
	trapsec = mc.RecSec(W=R*2,H=H) # Trap section
	orisec = mc.RecSec(W=w,H=H) # Orifice section
	switchsec = mc.RecSec(W=Ws,H=H) # Switch section

	# Traces
	cir.T([start + (R, -W/2), start + (R, -W/2-1)], secs=trapsec, trace_cap='round')
	orifice = cir.T([start + (R, -W/2-R), start + (R, -W/2-R-l)],secs=orisec)
	switch = cir.S(orifice.P2+(slop,-Ws/2), anchor='S', rotation=90, chan_sec=switchsec)
	cir.T([start|switch.S, switch.S], secs=switchsec)
	finish = switch.D|start
	cir.T([start,finish],secs=chansec)

	return finish
	
def main():
	design = mc.Design(backend='freecad')
	cir = design.create_circuit()
	
	x = design.origin
	for i in range(32):
		x = trap(cir,x)


	# Complete
	design.fuse()
	design.show()