import random
from copy import deepcopy
from itertools import product
from operator import add

from .chars import Player, Robot, Junk, gameclass
from .exceptions import BadTileError, LevelComplete, GameOver

from .debug import log

class GameGrid:
    
    """The game grid.
    
    The z-axis represents the vertical depth of the grid. The x and y
    axes refer to the columns and rows, respectively, of each z-level
    when viewed from above.
    
    The origin (0, 0, 0) should be at the bottom-left corner of the plan, and
    the "furthest" away from the viewer.
    
    The grid handles character placement, movement and collisions."""

    
    def __init__(self, x, y, z, game):
        self.game = game
        self.grid = self.get_empty_grid(x, y, z)
        self.objects = set()
        self.x = x
        self.y = y
        self.z = z
    
    def get_empty_grid(self, x, y, z):
        """Creates an empty grid of the appropriate dimensions and
        binds it to the current instance."""
        return [[[None for i in range(x)] for j in range(y)] for k in range(z)]
    
    def clear_grid(self):
        for obj in self.objects:
            #log('removing {} from {}'.format(gameclass(obj), obj.coords))
            self.clear_tile(obj.coords)
    
    def clear_tile(self, coords):
        self.set_tile(coords, None)
    
    def set_tile(self, coords, new):
        incumbent = gameclass(self.get_tile(coords))
        log('setting {} ({}) to {}'.format(coords, incumbent, gameclass(new)))
        x, y, z = coords
        self.grid[z][y][x] = new
        #log('setting {} to {}'.format(coords, gameclass(new)))

    def get_tile(self, coords):
        x, y, z = coords
        try:
            return self.grid[z][y][x]
        except IndexError:
            raise BadTileError('Cannot get tile at {},{},{}: Tile not in grid'.format(x, y, z))
    
    def get_random_coords(self):
        coords = [
            random.randint(0, self.x-1),
            random.randint(0, self.y-1),
            random.randint(0, self.z-1)
            ]
        return coords
    
    def get_random_empty_coords(self):
        while True:
            coords = self.get_random_coords()
            if self.tile_is_empty(coords):
                return coords
    
    def tile_is_empty(self, coords):
        return gameclass(self.get_tile(coords)) == 'empty'
    
    def tile_is_safe(self, coords):
        # TODO: Don't do this call to product every time. Generate neighbours
        # once and reuse it.
        # Maybe create a separate get_neighbours func, which takes coords
        # and returns list of absolute coords of neighbours.
        neighbours = product((-1, 0, 1), repeat=3)
        for n in neighbours:
            try:
                gc = gameclass(self.get_tile(map(add, coords, n)))
            except BadTileError:
                # Tile is out of bounds, and therefore not dangerous.
                continue
            if gc == 'robot':
                return False
        return True
    
    def is_valid_tile(self, coords):
        x, y, z = coords
        return (min(coords) >= 0) and (x <= self.x) and (y <= self.y) and (z <= self.z)
    
    def populate(self, enemies):
        self.clear_grid()
        _enemies = set()
        while enemies:
            coords = self.get_random_empty_coords()
            robot = Robot(coords, self)
            _enemies.add(robot)
            self.set_tile(coords, robot)
            enemies -= 1
        self.enemies = _enemies
        self.objects = _enemies.copy()
        coords = self.get_random_empty_coords()
        self.player = Player(coords, self)
        self.set_tile(coords, self.player)
        self.objects.add(self.player)
    
    def place_char(self, new):
        # NOTE: There is a major bug whereby when we restart the game after dying,
        # old robots have not been removed; they are not in grid.objects, and they
        # do not move, but they remain on the grid.
        # Logging indicated that when clear_grid() tries to remove objects from the grid,
        # the coords given by those objects do not actually correspond to the position of
        # the object on the grid.
        # This only happens when the player dies and restarts the game; not when the player
        # reaches the next level.
        # NOTE: It appears that even when the level is complete, calling set_tile on the robots
        # does nothing, because robots are already gone; all that is left is junk, which is
        # successfully cleared. When we restart after dying, junk is also cleared, but robots
        # are not. Therefore, it seems that robots are only truly cleared from the grid when
        # they die.
        coords = new.coords
        incumbent = self.get_tile(coords)
        if new == incumbent:
            # Character has not moved.
            # Happens when player tries to move out of bounds or stays still.
            # NOTE: Logging appears to indicate this is never used?
            return
        incumbent_cls = gameclass(incumbent)
        new_cls = gameclass(new)
        # Player is prevented from moving onto occupied tile before this stage;
        # therefore, if incumbent_cls != 'empty', new must be robot.
        if (incumbent_cls == 'empty') or (new_cls == 'empty'):
            self.set_tile(coords, new)
        elif incumbent_cls == 'player':
            # Robot collides with player; player dies, game over.
            # However, we have to keep going and move all robots to their
            # intended positions, so that the grid clears properly if the
            # player chooses to play again.
            # NOTE: I thought this would have fixed the problem, but it hasn't.
            log('robot killed player at {}'.format(new.coords))
            log('player coords: {}'.format(self.player.coords))
            self.player.is_alive = False
            self.set_tile(coords, new)
        elif incumbent_cls == 'robot':
            self.kill(incumbent)
            self.kill(new)
            j = Junk(coords, self)
            self.set_tile(coords, j)
            self.objects.add(j)
        elif incumbent_cls == 'junk':
            self.kill(new)
        else:
            log('None of the place_char conditions are met.')
            log('incumbent_cls: {}; new_cls: {}'.format(incumbent_cls, new_cls))
    
    def kill(self, enemy):
        # Killed object is not removed from self.enemies until after
        # all enemies have moved, as the size of the set cannot be changed
        # during iteration.
        enemy.is_alive = False
        if self.game.waiting:
            self.game.wait_bonus += int(enemy.__killscore__ * 1.1)
        else:
            self.game.score += enemy.__killscore__

    def move_enemies(self):
        # Moving enemies has several stages.
        # - Each enemy decides where it wants to move, and adjusts its
        #   internally stored coords (obj.coords) accordingly.
        #   Invalid moves must be detected and handled at this point, before
        #   coords are changed.
        # - After all enemies have adjusted their coords, each enemy is then
        #   placed in its new position on the grid.
        #   Collisions are handled at this point.
        # - Dead enemies are removed from self.enemies.
        for e in self.enemies:
            e.move()
        for e in self.enemies:
            self.place_char(e)
        if not self.player.is_alive:
            raise GameOver(False, 'You died!')
        dead_enemies = {e for e in self.enemies if not e.is_alive}
        #log(dead_enemies)
        self.enemies.difference_update(dead_enemies)
        log(self.objects.intersection(dead_enemies))
        self.objects.difference_update(dead_enemies)
        if not self.enemies:
            raise LevelComplete

    # Player can only view one "floor" of the grid at a time, and always views
    # the grid in plan. Player can cycle between floors at will.
    
    def view_plan(self, elev=None):
        if elev is None:
            elev = self.player.coords[2]
        plan = self.grid[elev]
        return plan
    