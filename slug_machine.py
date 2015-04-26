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
		StateMachine.__init__(self, SlugStateMachine.Idle())
		SlugStateMachine.OrderStates = {
			"a": SlugStateMachine.Attack(),
			"b": SlugStateMachine.Build(),
			"h": SlugStateMachine.Harvest(),
			"i": SlugStateMachine.Idle()
			# Move is indexed on a tuple, so special case that out when getting a move order
		}
		SlugStateMachine.MessageMap = {
			"order":  self.get_order,
			"collide": self.handle_collision,
			"timer": self.handle_timer
		}

	def get_state_for_stuff(self, message, details):
		if SlugStateMachine.MessageMap.has_key(message):
			return SlugStateMachine.MessageMap[message](details)
		else:
			print "Unhandled Message: ", message

	def get_order(self, details):
		if type(details) is tuple:
			return SlugStateMachine.Move()
		elif SlugStateMachine.OrderStates.has_key(details):
			return SlugStateMachine.OrderStates[details];
		else:
			print "Unhandled order: ", details

	def handle_collision(self, details):
		print "Unhandled collision"
		pass

	def handle_timer(self, details):
		print "Unhandled timer"
		pass

	def transition(self, message, details):
		nextState = self.get_state_for_stuff(message, details)
		self.currentState = self.currentState.next(str(nextState))
		# if nextState:
		# 	self.currentState = nextState


# State base class
class State:
	def run(self):
		assert 0, "run not implemented"
	def next(self, inp):
		assert 0, "next not implemented"
	def __str__(self):
		return str(self.__class__.__name__)

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
		if self.transitions and self.transitions.has_key(inp):
			return self.transitions[inp]
		else:
			print "Input not supported: ", inp
			return self
			# raise "Input not supported for current state"

class SlugStateT(StateT):
	# def next(self, inp, details=None):
	# 	potentialTransition = StateT.next(self, inp)
	# 	handleDetails = getattr(potentialTransition, "handle_details", None)
	# 	if potentialTransition and callable(handle_details): #TODO: real thing
	# 		return potentialTransition.handle_details(details)
	# 	else:
	# 		return potentialTransition
	# Create a default list of transitions that reacts to orders and collisions
	def lazy_init(self):
		pass
		# self.transitions = {
		# 	"order":OrderStateMachine, # move, attack, idle, harvest, build
		# 	"collide":CollisionStateMachine # mantis, resource, nest
		# }

# States
class SSIdle(SlugStateT):
	def run(self):
		# TODO: Stop everything
		print "Idling"

class SSAttack(SlugStateT):
	def run(self):
		# TODO: attack a thing
		print "Attack"

class SSBuild(SlugStateT):
	def run(self):
		print "Build"

class SSHarvest(SlugStateT):
	def run(self):
		print "Harvest"

class SSFlee(SlugStateT):
	def run(self):
		print "Flee"

class SSHasResources(SlugStateT):
	pass

class SSDumpResources(SlugStateT):
	pass

class SSHeal(SlugStateT):
	pass

class SSMove(SlugStateT):
	pass

SlugStateMachine.Attack = SSAttack
SlugStateMachine.Idle = SSIdle
SlugStateMachine.Build = SSBuild
SlugStateMachine.Harvest = SSHarvest
SlugStateMachine.Heal = SSHeal
SlugStateMachine.Move = SSMove




