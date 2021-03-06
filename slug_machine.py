# A state machine for slugs
class SlugStateMachine():
	def __init__(self, body):
		self.body = body
		self.has_resource = False
		# Initialize to idle
		self.currentState = SlugStateMachine.Idle()
		self.currentState.run(self.body)
		SlugStateMachine.OrderStates = {
			"a": SlugStateMachine.Attack,
			"b": SlugStateMachine.Build,
			"h": SlugStateMachine.Harvest,
			"i": SlugStateMachine.Idle
			# Move is indexed on a tuple, so special case that out when getting a move order
		}
		SlugStateMachine.MessageMap = {
			"order":  SlugStateMachine.get_order,
			"collide": SlugStateMachine.handle_collision,
			"timer": SlugStateMachine.handle_timer
		}

	def get_state_for_stuff(self, message, details):
		if SlugStateMachine.MessageMap.has_key(message):
			return SlugStateMachine.MessageMap[message](self, details)
		else:
			print "Unhandled Message: ", message

	def get_order(self, details):
		if type(details) is tuple:
			return SlugStateMachine.Move(details)
		elif SlugStateMachine.OrderStates.has_key(details):
			return SlugStateMachine.OrderStates[details]();
		else:
			print "Unhandled order: ", details

	def handle_collision(self, details):
		return self.currentState.handle_collision(self.body, details)

	def handle_timer(self, details): #TODO: revisit timer
		print self.currentState
		return self.currentState

	def transition(self, message, details):
		if message is not 'collide': print message, details
		nextState = self.get_state_for_stuff(message, details)
		self.currentState = self.currentState.next(nextState)
		try:
			self.currentState.run(self.body)
		except ValueError:
			print "Something wasn't found, idling"
			self.currentState = SlugStateMachine.Idle()
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

class SlugStateT(StateT):
	def lazy_init(self):
		self.transitions = {
			"SSMove":SlugStateMachine.Move,
			"SSIdle":SlugStateMachine.Idle,
			"SSAttack":SlugStateMachine.Attack,
			"SSBuild":SlugStateMachine.Build,
			"SSHarvest":SlugStateMachine.Harvest,
			"SSFlee":SlugStateMachine.Flee
		}
	def run(self, body):
		assert 0, "run not implemented"

	def next(self, inp):
		if not self.transitions:
			self.lazy_init()
		if self.transitions and self.transitions.has_key(str(inp)):
			return inp
		else:
			print "Input not supported: ", inp
			return self
	def handle_collision(self, body, details):
		what = details['what']
		who = details['who']
		if what is "Mantis" and body.amount < 0.5:
			print "Starting to flee"
			return SlugStateMachine.Flee()
		else:
			return self


# States
class SSIdle(SlugStateT):
	def run(self, body):
		body.stop()

class SSAttack(SlugStateT):
	def run(self, body):
		target = body.find_nearest("Mantis")
		body.follow(target)
		body.set_alarm(1)

	def handle_collision(self, body, details):
		what = details['what']
		who = details['who']
		if what is "Mantis":
			who.amount -= 0.05
		return SlugStateT.handle_collision(self, body, details)

class SSBuild(SlugStateT):
	def run(self, body):
		target = body.find_nearest("Nest")
		body.follow(target)
		body.set_alarm(1)

	def handle_collision(self, body, details):
		what = details['what']
		who = details['who']
		if what is "Nest":
			who.amount += 0.01
			if who.amount > 1.0:
				who.amount = 1.0
				return SlugStateMachine.Idle()
		return SlugStateT.handle_collision(self, body, details)

class SSHarvest(SlugStateT):
	def run(self, body):
		if body.has_resource:
			target = body.find_nearest("Nest")
		else:
			target = body.find_nearest("Resource")
		body.follow(target)
		body.set_alarm(1)

	def handle_collision(self, body, details):
		what = details['what']
		who = details['who']
		if what is "Resource" and not body.has_resource:
			body.has_resource = True
			who.amount -= 0.25
		elif what is "Nest":
			body.has_resource = False
		return SlugStateT.handle_collision(self, body, details)

class SSFlee(SlugStateT):
	def run(self, body):
		target = body.find_nearest("Nest")
		body.follow(target)
		body.set_alarm(1)

	def handle_collision(self, body, details):
		what = details['what']
		who = details['who']
		# Heal when colliding with a nest
		if what is "Nest":
			body.amount += 0.05
			if body.amount >= 1.0:
				body.amount = 1.0
				return SlugStateMachine.Idle()
		return self

class SSMove(SlugStateT):
	def __init__(self, target):
		SlugStateT.__init__(self)
		self.target = target
	def run(self, body):
		body.go_to(self.target)
		body.set_alarm(1)

SlugStateMachine.Attack = SSAttack
SlugStateMachine.Idle = SSIdle
SlugStateMachine.Build = SSBuild
SlugStateMachine.Harvest = SSHarvest
SlugStateMachine.Move = SSMove
SlugStateMachine.Flee = SSFlee




