#! python3

# This program is heavily dependent on the Pyglet module.
## Please ensure you're using Pyglet v1.3
### The Source Code used should follow PEP-8 guidelines.
""" Pycraft - the Pythonic version of Minecraft """

#                   For Mom and Dad;
#               You believed in me, when even I did not.

import math

import random

import sys

import time

from collections import deque
from pyglet import image
from pyglet.gl import *
from pyglet.graphics import TextureGroup
from pyglet.window import key, mouse

TICKS_PER_SEC = 60

SECTOR_SIZE = 16

WALKING_SPEED = 5

FLYING_SPEED = 15

GRAVITY = 21.0

MAX_JUMP_HEIGHT = 1.0
# This is approximately the height of a single block.

""" Not going to lie - had to google these maths """

JUMP_SPEED = math.sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)
TERMINAL_VELOCITY = 50

PLAYER_HEIGHT = 2
# Because we don't need Yao Ming running around.

if sys.version_info[0] >= 3:
# version_info[0] is the equivalent to sys.version_info.major
    xrange = range

# You're going to see dy, dx, and dz appear a LOT.
# These are the cube faces on each axis of a coordinate plane
# dx - X axis
# dy - Y axis
# dz - Z axis
# dt - Distance traveled in that tick

# ^ ^
# | |

# Those are primarily used to encapsulate vectors

def cube_vertices(x, y, z, n):
    """ Return the vertices of the cube at positions x, y, z with the size of 2*n """
    return [
        x-n,y+n,z-n, x-n,y+n,z+n, x+n,y+n,z+n, x+n,y+n,z-n,  # top
        x-n,y-n,z-n, x+n,y-n,z-n, x+n,y-n,z+n, x-n,y-n,z+n,  # bottom
        x-n,y-n,z-n, x-n,y-n,z+n, x-n,y+n,z+n, x-n,y+n,z-n,  # left
        x+n,y-n,z+n, x+n,y-n,z-n, x+n,y+n,z-n, x+n,y+n,z+n,  # right
        x-n,y-n,z+n, x+n,y-n,z+n, x+n,y+n,z+n, x-n,y+n,z+n,  # front
        x+n,y-n,z-n, x-n,y-n,z-n, x-n,y+n,z-n, x+n,y+n,z-n,  # back
        ]
# Creation of the 3D cube for Pyglet.gl

def texture_coordinate(x, y, n=4):
    """ Bound the vertices to the textured square 
    """
    m = 1.0 / n
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m
# Pretty self explanitory - googled the math though.

def texture_coordinates(top, bottom, side):
    """ Return a list of the textured squares for each side of the square 
    """
    top = texture_coordinate(*top)
    bottom = texture_coordinate(*bottom)
    side = texture_coordinate(*side)
    result = [] # We need a home for the list, after all
    result.extend(top)
    result.extend(bottom)
    result.extend(side * 4)
    return result

TEXTURE_PATH = 'BlockTextures.png'
# Basic block textures to be expanded further later on
GRASS = texture_coordinates((1,0), (0,1), (0,0))
SAND = texture_coordinates((1,1), (1,1), (1,1))
BRICK = texture_coordinates((2,0), (2,0), (2,0))
STONE = texture_coordinates((2,1), (2,1), (2,1))

# Faces of the block, obviously.
FACES = [
    (0, 1, 0),
    (0, -1, 0),
    (-1, 0, 0),
    (1, 0, 0),
    (0, 0, 1),
    (0, 0, -1),
]

def normalize(position):
    """ Accepts the 'position' of random precision, and returns the block
which contains that position

    Params
    -------
    position: tuple of the len(3)

    then Returns:
    -------
    block_position: tuple of ints of len(3)
    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y ,z)
    # Rounding off the coordinates - no need for HxC precision, amirite

def sectorize(position):
    """ Returns a tuple representing the sector for the given block position """
    x, y, z = normalize(position)
    x, y, z = x // SECTOR_SIZE, y // SECTOR_SIZE, z // SECTOR_SIZE
    return (x, 0, z)

class Model(object):

    def __init__(self):
        # Collection of vertex lists to render in batches
        self.batch = pyglet.graphics.Batch()

        # A group to manage the OpenGL texture
        self.group = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # A ObjRelMap from player position to the texture of the indicated block
        # at that position - this holds all the blocks currently sitting in the world
        self.world = {}

        # Same as above - but only holds the blocks that are visible
        self.shown = {}

        # ObjRelMap from player position to a pyglet VertexList for all visible blocks
        self._shown = {}

        # ObjRelMap from current sector to a list of coordinate positions
        # within that sector.
        self.sectors = {}

        # A simplistic function to queue implementation. This is populated with
        # _show_block() and _hide_block() calls
        self.queue = dequeue()

        self._initialize()

    def _initialize(self):
        """ Initialize the world, BY FILLING IT """
        n = 80 # approx. HALF the w/h of the entire world.
        s = 1 # step size
        y = 0 # initial Y height
        for x in range(-n, n + 1, s):
            for z in xrange(-n, n + 1, s):
                # Create a layer of stone and grass throughout. Then take a nap
                self.add_block((x, y - 2, z), GRASS, immediate=False)
                self.add_block((x, y - 3, z), STONE, immediate=False)
                if x in (-n, n) or z in (-n, n):
                    # create outer walls of the world. YAY FLAT EARTH
                    for dy in xrange(-2, 3):
                        self.add_block((x, y + dy, z), STONE, immediate=False)

        # Generate hills in the world randomly. Ugh, so immersive
        o = n -10
        for _ in xrange(120):
            a = random.randint(-o, o) # x position of the created hill
            b = random.randint(-o, o) # z position of the created hill
            c = -1 # base of the created hill
            h = random.randint(1, 6) # height
            s = random.randint(4, 8) # side length of the hill. (2 * s)
            d = 1 # taper off the hills or naw
            t = random.choice([GRASS, SAND, BRICK])
            for y in xrange(c, c + h):
                for x in xrange(a - s, a + s + 1):
                    for z in xrange(b - s, b + s + 1):
                        if (x - a) ** 2 + (z -b) ** 2 > (s + 1) ** 2:
                            continue
                        if (x - 0) ** 2 + (z - 0) * 2 < 5 ** 2:
                            continue
                        self.add_block((x, y, z), t, immediate=False)
    def hit_test(self, position, vector, max_distance=8):
        """ LOS search from player position. If block is hit and returned, along with the
block previously in the LOS. If no block is found - return nothing. Nothing at all
        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in xrange(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous # here's where you'll get None/None
            previous = key
            x, y, z = z + dx / m, y + dy / m, z + dz / m
        return None, None # told you

    def exposed(self, position):
        """ Returns False if the given position is surrounded on all 6 sides. If not, is True
        """
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
            return False

    def add_block(self, position, texture, immediate=True):
        """ Add a block with the selected texture and placement to the world """
        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = texture
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)

    def remove_block(self, position, immediate=True):
        """ The lord giveth, and the lord taketh """
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors

    def check_neighbors(self, position):
        """ Check for the sides of the current block, are they blocked? Do they have friends? I wish I had friends.
    This means hiding blocks that aren't exposed, and exposed blocks are shown. Usually used after a block is added/removed
        """
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position, immediate=True):
        """ Method to show the block given at the arbitrary position. This method is assuming the 
    block as already been added with the previous class method - add_block()
        """
        texture = self.world[position]
        self.shown[position] = texture
        if immediate:
            self._show_block(position, texture)
        else: self._enqueue(self._show_block, position, texture)

    def _show_block(self, position, texture):
        """ Private method implementation of show_block() """
# I'm using texture_coordinates() to generate the block form        
        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data= list(texture)
        # bring a vertex list to life
# TODO: Possibly look into add_indexed() method rather than the following method. *nervous laughs*
        self._shown[position] = self.batch.add(24, GL_QUADS, self.group,
            ('v3f/static', vertex_data)
            ('t2f/static', texture_data))

    def hide_block(self, position, immediate=True):
        """ Hide the block from the given player position, and player view. Hiding the block doesn't
    remove the block from the world. Nor remove it's feelings.
    ha.
        """
        self.shown.pop(position) # pops it off, then returns it
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)
# Good lord, do I hate the word queue.
# .... Queueeueueue?

    def _hide_block(self, position):
        """ Private implementation of hide_block() """
        self._shown.pop(position).delete()

    def show_sector(self, sector):
        """ I make sure that all the blocks in the given sector that SHOULD be seen, are drawn to the canvas.
        like little happy clouds.
            that happy cloud will be our lil' secret.
        """
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector):
        """ Byeeeee cloud """
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sector(self, before, after):
        """ Move from the previous sector of the world, to the 'after'. (So philosphical. is there an after?)
    Anyway......... subdividing the world into sectors help render the world quicker.
        """
        before_set = set()
        after_set = set()
        pad = 4
        for dx in xrange(-pad, pad + 1):
            for dy in [0]: 
                for dz in xrange(-pad, pad + 1): # thank god for google, math is hard
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def enqueue(self, func, *args):
        """ Add func to the internal queue. queuueue. queueueueueueue? """
        self.queue.append((func, args))

    def _dequeue(self):
        """ Pop off the top function from the internal queueuueue and then call it. God I REALLY hate queue. """
        func, args = self.queue.poplet()
        func(*args)

    def process_queue(self):
        """ Process the entire queue while taking periodic CPU breaks... Allowing the game to run smoothly. The queue contains calls to
        _show_block() and hide_block(). This method should be called if add_block() or remove_block() was called with immediate=False
            If those methods are returning false, that's not good. Like... really not good.
        """
    def process_entire_queue(self):
        """ No CPU breaks. This method apparently endorses subpar working conditions. """
        while self.queue:
            self._dequeue()
# MARK: END OF MODEL CLASS


# MARK: BEGINNING OF WINDOW CLASS
class Window(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

    # Whether or not the Pyglet window created captures the mouse
        self.exclusive = False

    # When flying - gravity has no effect, because, well..... flying?
        self.flying = False 

    # Strafing is moving laterally
        self.strafe = [0,0]

    # Current position in the world - specified with floats. ( Tenths, hundredths, Thousandths...)
    # unlike normal coordinate planes - the Y axis is the vertical one.
        self.position(0, 0, 0)

    # First element is rotation of the player on the ground. ( Yeah - I googled this method.)
    # Rotation is in degrees.
    # Math is hard.
        self.rotation(0, 0, 0)

    # What sector am I in?
        self.sector = None

    # The crosshair dead-center of the screen
        self.reticle = None

    # Upward velocity initial value 
        self.dy = 0

    # Texture inventory
        self.inventory = [BRICK, GRASS, SAND]

    # The current block the user has in their selection
        self.block = self.inventory[0]
        # index 0 means the first in that list, 1 == 2, etc..
        # use num keys to cycle through

    # Convenience list of the number keys
        self.num_keys = [
        key._1, key._2, key._3, key._4,
        key._5, key._6, key._7, key._8,
        key._9, key._0
        ]

    # Instance of the model that handles the world.
    # ... Jesus is that you?
        self.model = Model()

    # Label displayed in the top-left of the pyglet canvas
        self.label = pyglet.text.Label('', font_name='Arial', font_size=18,
        x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
        color=(0, 0, 0, 255))

    # schedule the update() method to be called
    # TICKS_PER_SEC - The main game event loop.
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)

    def set_exclusive_mouse(self, exclusive):
        """ If exclusive is True - the game will capture the mouse movement. If false, ignore the mouse. """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ Return the player's current LOS - indicate the direction they're facing """
        x, y = self.rotation
# I googled the rest of the method - Lolmath.
        m = math.cos(math.radians(y))
# Basically - give certain values depending on whether or not player is staring straight at the ground
# or straight up in the air. But yeah... math.
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90))  * m
        dz = math.sin(math.radians(x - 90)) * m

        return (dx, dy, dz)

    def get_motion_vector(self):
        """ Return current player motion - indicating velocity """
        """ so.. much...mat... I mean google """

        if any(self.strafe):
            x, y = self.rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)
            if self.flying:
                m = math.cos(y_angle)
                dy = math.sin(y_angle)
                
                if self.strafe[1]:
                    # moving left or to the right
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    # You're going backwards
                    dy *= -1
                # when flying up, or down, you can't move left or right as easily.
                ## We can't always have nice things.
                dx = math.cos(x_angle) * m
                dz = math.sin(x_angle) * m
            else:
                dy = 0.0
                dx = math.cos(x_angle)
                dz = math.sin(x_angle)
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        """ This method is called repeatedly by the pyglet clock """
        self.model.process_queue()
        sector = sectorize(self.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue() # Because this was bad, remember?
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in xrange(m):
            self._update(dt / m)

    def _update(self, dt):
        """ Private implementation of the update() method - this is the home
            of the motion logic, gravity, and collision detection. Dr. Strange,
            are you in there?
        """
        # Walking  vvv
        
        speed = FLYING_SPEED if self.flying else WALKING_SPEED
        d = dt * speed # distance covered in that CPU tick
        dx, dy, dz = self.get_motion_vector()
        # New position in the space - prior to checking gravity method
        dx, dy, dz = dx * d, dy * d, dz * d
        
        # Gravity  vvv

        if not self.flying:
            # Update vertical speed: if you're falling - speed up until terminal
            # velocity - because ... that's what happens when you fall
            # If you're jumping - slow down until you begin to actually fall
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, - TERMINAL_VELOCITY)
            dy += self.dy * dt

        # Object collisions
        x, y, z = self.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.position = (x, y, z)

    def collide(self, position, height):
        """ Method to check if the player at the given vector is colliding with any
            physical blocks within the world.
        """
         # I had to google this implementation - but essentially - you're checking
         # whether or not you have overlap with the dimensions of a surrounding block
         # at the player position - if it's 0: touching terrain even slightly, counts as
         # collision - we don't want that. It's a real slippery scale. So - 0 == collision,
         # .49 means you're sinking straight into the ground - similar to walking through tall
         # grass. If it's anything greater than 50%.... you're falling through the ground.