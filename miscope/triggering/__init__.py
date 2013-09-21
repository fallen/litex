from migen.fhdl.std import *
from migen.flow.actor import *
from migen.flow.network import *
from migen.fhdl.specials import Memory
from migen.bus import csr
from migen.bank import description, csrgen
from migen.bank.description import *

class Term(Module, AutoCSR):
	def __init__(self, width):
		self.width = width

		self.sink = Sink([("d", width)])
		self.source = Source([("hit", 1)])

		self.busy = Signal()

		self._r_trig = CSRStorage(width)
		self._r_mask = CSRStorage(width)

		###

		trig = self._r_trig.storage
		mask = self._r_mask.storage

		hit = Signal()

		self.comb +=[
			hit.eq((self.sink.payload.d & mask) == trig),
			self.source.stb.eq(self.sink.stb),
			self.sink.ack.eq(self.sink.ack),
			self.source.payload.hit.eq(hit)
		]

class Sum(Module, AutoCSR):
	def __init__(self, ports=4):
		
		self.sinks = [Sink([("hit", 1)]) for p in range(ports)]
		self.source = Source([("hit", 1)])
		
		self._r_prog_we = CSRStorage()
		self._r_prog_adr = CSRStorage(ports) #FIXME
		self._r_prog_dat = CSRStorage()

		mem = Memory(1, 2**ports)
		lut_port = mem.get_port()
		prog_port = mem.get_port(write_capable=True)

		self.specials += mem, lut_port, prog_port

		###

		# Lut prog
		self.comb +=[
			prog_port.we.eq(self._r_prog_we.storage),
			prog_port.adr.eq(self._r_prog_adr.storage),
			prog_port.dat_w.eq(self._r_prog_dat.storage)
		]

		# Lut read
		for i, sink in enumerate(self.sinks):
			self.comb += lut_port.adr[i].eq(sink.payload.hit)

		# Drive source
		self.comb +=[
			self.source.stb.eq(optree("&", [sink.stb for sink in self.sinks])),
			self.source.payload.hit.eq(lut_port.dat_r),
			[sink.ack.eq(self.source.ack) for sink in self.sinks]
		]


class Trigger(Module, AutoCSR):
	def __init__(self, width, ports):
		self.width = width
		self.ports = ports
		
		self.submodules.sum = Sum(len(ports))

		# FIXME : when self.submodules +=  is used, 
		# get_csrs() is not called
		for i, port in enumerate(ports):
			tmp = "self.submodules.port"+str(i)+" = port"
			exec(tmp)

		self.sink   = Sink([("d", width)])
		self.source = self.sum.source
		self.busy = Signal()

		###
		for i, port in enumerate(ports):
			self.comb +=[
				port.sink.stb.eq(self.sink.stb),
				port.sink.payload.d.eq(self.sink.payload.d),
				port.source.connect(self.sum.sinks[i])
			]