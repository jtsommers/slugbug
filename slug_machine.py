from slug_states import State, Idle

# A simple base class for a state machine
class StateMachine:
	def __init__(self, initialState):
		self.currentState = initialState
		self.currentState.run()
	# Template method:
	def runAll(self, inputs):
		for i in inputs:
			print(i)
			self.currentState = self.currentState.next(i)
			self.currentState.run()

# A state machine for slugs
class SlugStateMachine(StateMachine):
	def __init__(self):
		# Initialize to idle
		StateMachine.__init__(self, SlugStateMachine.Idle)
