
import Tkinter
import collections
import random
import sys
import math
import heapq

class World:
  """container for many GameObject instances and some global parameters"""

  def __init__(self, width, height):
    self.width = width
    self.height = height
    self.all_objects = []
    self.objects_by_class = collections.defaultdict(list)
    self.sel_a = None
    self.sel_b = None
    self.selection = {}
    self.time = 0

  def register(self, obj):
    """add a GameObject to the all_objects and objects_by_class lists"""
    assert isinstance(obj, GameObject)

    if obj not in self.all_objects:
      self.all_objects.append(obj)

    clazz = obj.__class__
    if obj not in self.objects_by_class[clazz]:
      self.objects_by_class[clazz].append(obj)
 
  def unregister(self, obj):
    """remove a GameObject from the all_objects and objects_by_class lists"""
    assert isinstance(obj, GameObject)
    if obj in self.all_objects:
      self.all_objects.remove(obj)

    clazz = obj.__class__
    if obj in self.objects_by_class[clazz]:
      self.objects_by_class[clazz].remove(obj)

    if obj in self.selection:
      del self.selection[obj]

  def draw(self,canvas):
    """draw the whole game world to the canvas"""

    canvas.delete(Tkinter.ALL)

    # backdrop
    canvas.create_rectangle(0, 0, self.width, self.height, fill='#eba', outline='')

    # child objects
    for obj in self.all_objects:
      obj.draw(canvas)

    # highlight selected objects
    if self.selection:
      for c in self.selection:
        canvas.create_rectangle(
            c.position[0]-c.radius-1,
            c.position[1]-c.radius-1,
            c.position[0]+c.radius+1,
            c.position[1]+c.radius+1,
            outline='green',
            fill='',
            width=2.0)

    # draw the user's partial selection box 
    if self.sel_a and self.sel_b:
      top_left = (min(self.sel_a[0], self.sel_b[0]), min(self.sel_a[1], self.sel_b[1]))
      bottom_right = (max(self.sel_a[0], self.sel_b[0]), max(self.sel_a[1], self.sel_b[1]))
      canvas.create_rectangle(
          top_left[0],
          top_left[1],
          bottom_right[0],
          bottom_right[1],
          outline='green',
          fill='',
          width=2.0)

  def build_distance_field(self, target, blockers=[], expansion=0):
    """build a low-resolution distance map and return a function that uses
    bilinear interpolation to look up continuous positions"""

    bin_size = 20

    obstacles = {} # (i,j) -> bool 

    # paint no-obstacles over the map
    for i in range(self.width/bin_size):
      for j in range(self.height/bin_size):
        obstacles[(i,j)] = False

    # rasterize collision space of each object
    for obj in blockers:
      i_lo = int((obj.position[0] - obj.radius)/bin_size - 1)
      i_hi = int((obj.position[0] + obj.radius)/bin_size + 1)
      j_lo = int((obj.position[1] - obj.radius)/bin_size - 1)
      j_hi = int((obj.position[1] + obj.radius)/bin_size + 1)
      for i in range(i_lo, i_hi+1):
        for j in range(j_lo, j_hi+1):
          x, y = i*bin_size, j*bin_size
          dx = obj.position[0]-x
          dy = obj.position[1]-y
          dist = math.sqrt(dx*dx+dy*dy)
          if dist < obj.radius + expansion:
            obstacles[(i,j)] = True

    # dijkstra's algorithm to build distance map
    dist = {}
    start = (int(target[0]/bin_size), int(target[1]/bin_size))
    dist[start] = 0
    queue = [(0,start)]
    while queue:
      d, c = heapq.heappop(queue)
      for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
        next_c = (c[0] + di, c[1] + dj)
        if next_c in obstacles:

          if not obstacles[next_c]:
            cost = 1
          else:
            cost = 1e6
          next_d = d + cost
          if next_c not in dist or next_d < dist[next_c]:
            dist[next_c] = d
            heapq.heappush(queue, (next_d, next_c))

    def lookup(position): # bilinear interpolation
      x,y = position
      alpha = float(x % bin_size)/bin_size
      beta = float(y % bin_size)/bin_size
      i, j = int(x / bin_size), int(y / bin_size)
      dx = x - self.width/2
      dy = y - self.height/2
      default = 2*math.sqrt(dx*dx+dy*dy)
      a = dist.get((i,j),default)
      b = dist.get((i+1,j),default)
      c = dist.get((i,j+1),default)
      d = dist.get((i+1,j+1),default)
      ab = (1-alpha)*a + alpha*b
      cd = (1-alpha)*c + alpha*d
      abcd = (1-beta)*ab + beta*cd
      return abcd

    return lookup

  def update(self, dt):
    """update the world and all registered GameObject instances"""

    self.time += dt

    # update all objects
    for obj in self.all_objects:
      obj.update(dt)

    # let brains handle collision reactions
    def handle_collision(a,b):
      if a.brain: a.brain.handle_event('collide',{'what': str(b.__class__.__name__), 'who': b})
      if b.brain: b.brain.handle_event('collide',{'what': str(a.__class__.__name__), 'who': a})

    # collide within species
    for animal in [Slug,Mantis]:
      self.eject_colliders(self.objects_by_class[animal],self.objects_by_class[animal],randomize=True)

    # collide across species
    self.eject_colliders(self.objects_by_class[Mantis],self.objects_by_class[Slug],randomize=True,handler=handle_collision)

    # collide animals with minerals without handlers
    for animal in [Slug,Mantis]:
      for mineral in [Obstacle]:
        self.eject_colliders(self.objects_by_class[animal],self.objects_by_class[mineral])

    # collide animals with minerals with handlers
    for animal in [Slug,Mantis]:
      for mineral in [Nest,Resource]:
        self.eject_colliders(self.objects_by_class[animal],self.objects_by_class[mineral],handler=handle_collision)

    # clean up objects with negative amount values
    for obj in self.all_objects:
      if obj.amount < 0:
        obj.destroy()
      elif obj.amount > 1:
        obj.amount = 1


  def eject_colliders(self, firsts, seconds, randomize=False, handler=None):
    
    def eject(o1, o2):
      if o1 != o2:
        dx = o1.position[0] - o2.position[0]
        dy = o1.position[1] - o2.position[1]
        dist = math.sqrt(dx*dx+dy*dy)
        if dist < o1.radius + o2.radius:
          extra = dist - (o1.radius + o2.radius)
          fraction = extra / dist
          if handler: handler(o1,o2) # let colliders know they collided!
          if randomize and random.random() < 0.5:
            o2.position = (o2.position[0] + fraction*dx, o2.position[1] + fraction*dy)
          else:
            o1.position = (o1.position[0] - fraction*dx, o1.position[1] - fraction*dy)

    def sorted_with_bounds(objects):
      return sorted([(o.position[0]-o.radius, 'add', o) for o in objects] +
                    [(o.position[0]+o.radius, 'remove', o) for o in objects])

    active_firsts = {}
    active_seconds = {}

    firsts_with_bounds = sorted_with_bounds(firsts)
    seconds_with_bounds = sorted_with_bounds(seconds)

    while firsts_with_bounds and seconds_with_bounds:

      o1_key, o1_cmd, o1 = firsts_with_bounds[0]
      o2_key, o2_cmd, o2 = seconds_with_bounds[0]

      if o1_key < o2_key:
        firsts_with_bounds.pop(0)
        if o1_cmd is 'add':
          active_firsts[o1] = True
          for o2 in active_seconds:
            eject(o1,o2)
        else:
          del active_firsts[o1]
      else:
        seconds_with_bounds.pop(0)
        if o2_cmd is 'add':
          active_seconds[o2] = True
          for o1 in active_firsts:
            eject(o1,o2)
        else:
          del active_seconds[o2]

  def populate(self, specification, brain_classes):
    """create an interesting randomized level design"""

    if 'worldgen_seed' in specification:
      random.seed(specification['worldgen_seed'])

    def random_position():
      return (random.random()*self.width, random.random()*self.height)

    for i in range(specification.get('nests',0)):
      n = Nest(self)
      n.position = random_position()
      self.register(n)

    for i in range(specification.get('obstacles',0)):
      o = Obstacle(self)
      o.radius = 5+250*random.random()*random.random()*random.random()
      o.position = random_position()
      self.register(o)

    for i in range(specification.get('resources',0)):
      r = Resource(self)
      r.position = random_position()
      r.amount = random.random()
      self.register(r)

    for i in range(specification.get('slugs',0)):
      s = Slug(self)
      s.position = random_position()
      s.brain = brain_classes['slug'](s)
      s.set_alarm(0)
      self.register(s)

    for i in range(specification.get('mantises',0)):
      m = Mantis(self)
      m.position = random_position()
      m.brain = brain_classes['mantis'](m)
      m.set_alarm(0)
      self.register(m)

    for i in range(10): # jiggle the world around for a while so it looks pretty
      self.eject_colliders(self.all_objects,self.all_objects,randomize=True)

  def find_nearest(self, searcher, clazz=None, where=None):
    """find the nearest object of the given class and property according to
    navigable distance"""

    field = self.build_distance_field(
        searcher.position,
        self.all_objects,
        -searcher.radius)

    if clazz:
      candidates = self.objects_by_class[clazz]
    else:
      candidates = self.all_objects

    return min(filter(where,candidates),key=lambda obj: field(obj.position))


  def issue_selection_order(self, order):
    """apply user's order (a key or right-click location) to the selected
    objects"""

    for obj in self.selection:
      if obj.brain:
        obj.brain.handle_event('order',order)

  def make_selection(self):
    """build selection from the set of units contained in the sel_a-to-sel_b
    bounding box"""

    top_left = (min(self.sel_a[0], self.sel_b[0]), min(self.sel_a[1], self.sel_b[1]))
    bottom_right = (max(self.sel_a[0], self.sel_b[0]), max(self.sel_a[1], self.sel_b[1]))
    self.selection = {}
    for obj in self.objects_by_class[Slug]:
      if      top_left[0] < obj.position[0] \
          and top_left[1] < obj.position[1] \
          and obj.position[0] < bottom_right[0] \
          and obj.position[1] < bottom_right[1]:
            self.selection[obj] = True
    self.sel_a = None
    self.sel_b = None

  def clear_selection(self):
    self.selection = {}

class Controller(object):
  """base class for simulation-rate GameObject controllers"""
  def update(self, obj, dt):
    pass

class ObjectFollower(Controller):
  """behavior of following another object via direct approach"""

  def __init__(self, target):
    self.target = target

  def update(self, obj, dt):
    dx = self.target.position[0] - obj.position[0]
    dy = self.target.position[1] - obj.position[1]
    mag = math.sqrt(dx*dx+dy*dy)
    obj.position = (obj.position[0] + dt*obj.speed*dx/mag,
                    obj.position[1] + dt*obj.speed*dy/mag)

class FieldFollower(Controller):
  """behavior of descending a given distance field"""

  def __init__(self, field):
    self.field = field

  def update(self, obj, dt):
    x, y = obj.position
    eps = 0.1
    gx = self.field((x+eps,y)) - self.field((x-eps,y))
    gy = self.field((x,y+eps)) - self.field((x,y-eps))
    mag = math.sqrt(gx*gx+gy*gy)
    if mag:
      obj.position = (obj.position[0] - dt*obj.speed*gx/mag,
                      obj.position[1] - dt*obj.speed*gy/mag)

class GameObject(object):
  """base class for objects managed by a World"""

  def __init__(self, world):
    self.world = world
    self.radius = 10
    self.color = 'gray'
    self.position = None
    self.controller = None
    self.brain = None
    self.amount = 1 # a generic value that is visualized in the graphics
    self.timer_deadline = None

  def __repr__(self):
    return '<%s %d>' % (str(self.__class__.__name__), id(self))

  def draw(self, canvas):
    """draw a generic object to the screen using it's position, radius, color, and amount"""
    if self.position:
      sa = math.sqrt(self.amount)
      canvas.create_oval(
          self.position[0]-self.radius*sa,
          self.position[1]-self.radius*sa,
          self.position[0]+self.radius*sa,
          self.position[1]+self.radius*sa,
          outline='',
          fill=self.color)
      canvas.create_oval(
          self.position[0]-self.radius,
          self.position[1]-self.radius,
          self.position[0]+self.radius,
          self.position[1]+self.radius,
          outline='black',
          fill='')


  def update(self, dt):
    """handle simulation-rate updates by delegating to controller"""
    if self.timer_deadline is not None:
      if self.timer_deadline < self.world.time:
        self.timer_deadline = None
        if self.brain:
          self.brain.handle_event('timer', None)

    if self.controller:
      self.controller.update(self, dt)

  def go_to(self, target):
    blockers = [obj for obj in self.world.all_objects if obj is not target and obj is not self]
    position = target.position if isinstance(target, GameObject) else target
    field = self.world.build_distance_field(position, blockers, self.radius)
    field_follower = FieldFollower(field)
    self.controller = field_follower

  def find_nearest(self, classname):
    clazz = eval(classname)
    return self.world.find_nearest(self, clazz)

  def follow(self, target):
    self.controller = ObjectFollower(target)

  def stop(self):
    self.controller = None

  def destroy(self):
    self.world.unregister(self)

  def set_alarm(self, dt):
    when = self.world.time + dt
    if self.timer_deadline is None or when < self.timer_deadline:
      self.timer_deadline = when

class Nest(GameObject):
  """home-base for Team Slug"""
  def __init__(self, world):
    super(Nest, self).__init__(world)
    self.radius = 100
    self.amount = 0.5
    self.color = 'orange'
  
class Obstacle(GameObject):
  """an impassable rocky obstacle"""
  def __init__(self, world):
    super(Obstacle, self).__init__(world)
    self.radius = 25
    self.color = 'gray'

class Resource(GameObject):
  """a tasty clump of resources to be consumed"""
  def __init__(self, world):
    super(Resource, self).__init__(world)
    self.radius = 25
    self.color = 'cyan'

class Slug(GameObject):
  """fearless, inhuman, slimy protagonists"""
  def __init__(self, world):
    super(Slug, self).__init__(world)
    self.goal = None
    self.time_to_next_decision = 0
    self.speed = 100
    self.radius = 20
    self.color = 'yellow'

class Mantis(GameObject):
  """indigenous lifeforms, mostly harmless"""
  
  def __init__(self, world):
    super(Mantis, self).__init__(world)
    self.time_to_next_decision = 0
    self.target = None
    self.speed = 200
    self.radius = 5
    self.color = '#484'

import p4_brains

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600

master = Tkinter.Tk()
master.title("Tears of the Mantis: Legends of Xenocide")

world = World(CANVAS_WIDTH, CANVAS_WIDTH)
world.populate(p4_brains.world_specification, p4_brains.brain_classes)

canvas = Tkinter.Canvas(master, width=CANVAS_WIDTH, height=CANVAS_HEIGHT) 
canvas.pack()

SIMULATION_TICK_DELAY_MS = 10.0
GRAPHICS_TICK_DELAY_MS = 30.0

def global_simulation_tick():
  world.update(SIMULATION_TICK_DELAY_MS/1000.0)
  master.after(int(SIMULATION_TICK_DELAY_MS), global_simulation_tick)

def global_graphics_tick():
  world.draw(canvas)
  master.after(int(GRAPHICS_TICK_DELAY_MS), global_graphics_tick)

master.after_idle(global_simulation_tick)
master.after_idle(global_graphics_tick)

def left_button_down(event):
  world.sel_a = (event.x, event.y)
  if world.selection:
    world.clear_selection()

def left_button_double(event):
  world.sel_a = (0,0)
  world.sel_b = (world.width, world.height)
  world.make_selection()

def left_button_move(event):
  if world.sel_a:
    world.sel_b = (event.x, event.y)

def left_button_up(event):
  if world.sel_a:
    world.sel_b = (event.x, event.y)
    world.make_selection()

def right_button_down(event):
  world.issue_selection_order((event.x, event.y))

def key_down(event):
  world.issue_selection_order(event.char)

master.bind('<ButtonPress-1>', left_button_down)
master.bind('<Double-Button-1>', left_button_double)
master.bind('<B1-Motion>', left_button_move)
master.bind('<ButtonRelease-1>', left_button_up)
master.bind('<ButtonPress-2>', right_button_down)
master.bind('<Key>', key_down)
master.bind('<Escape>', lambda event: master.quit())

master.mainloop()
