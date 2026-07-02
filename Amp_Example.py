import microcad as mc

def main():
	# design = mc.Design(backend='fusion')
	design = mc.Design(backend='freecad')
	cir = design.create_circuit()
	# Circuit Components
	tran1 = cir.M((0,0,0),anchor='S') # Transistor
	trace1 = cir.T([tran1.D,tran1.D+(0,-500)]) # Short trace to resistor
	res1 = cir.R(trace1.P2,50,anchor='L',rotation=-90) # Resistor of 50 kPa*s/uL
	# Ports
	sup1 = cir.V(tran1.S+(0,5000)) # Supply Port
	gnd1 = cir.V(res1.R+(0,-5000)) # Ground Port
	out1 = cir.V((sup1.C%gnd1.C)+(6000,1000)) # Output Port
	inp1 = cir.V(tran1.G1+(-6000,0),zspan=[0,-cir.params['sub_H']]) # Input Port
	# Traces
	cir.T([sup1.C,tran1.S])
	cir.T([res1.R,gnd1.C])
	cir.T([tran1.D+(0,-250),tran1.D+(1000,-250),out1.C],trace_R=1000)
	cir.T([tran1.G1,inp1.C],secs=mc.CurveSec(W=250,H=-30))
	# Complete
	design.fuse()
	design.show()
	design.slice_dxf([25,-15], 'Amp_Example')