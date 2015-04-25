# State base class
class State:
	def run(self):
		assert 0, "run not implemented"
	def next(self, inp):
		assert 0, "next not implemented"

# Base class for a state with a transitions map
class StateT(State):
	def __init__(self):
		self.transitions = None
	# Lazily initialize the transition map, needs to be overwritten
	def lazy_init(self):
		assert 0, "lazy_init not implemented"
	def next(self, inp):
		if not self.transitions:
			self.lazy_init()
		if self.transitions.has_key(inp):
			return self.transitions[inp]
		else:
			print "Input not supported: ", inp
			raise "Input not supported for current state"
