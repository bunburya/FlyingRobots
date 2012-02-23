"""A basic curses interface for FlyingRobots."""

import curses

from game import Game
from exceptions import LevelComplete, GameOver
from chars import gameclass

from debug import log

def ctrl(ch):
    return chr(ord(ch)-96)

def unctrl(ch):
    return chr(ord(ch)+96) if is_ctrl(ch) else ch

def is_ctrl(ch):
    return 1 <= ord(ch) <= 26

class GameInterface:
    
    charmap = {
        'robot':    '+',
        'player':   '@',
        'empty':    ' ',
        'junk':     '*'
        }
    
    xy_move_keys = {
        'h':    (-1, 0),
        'j':    (0, 1),
        'k':    (0, -1),
        'l':    (1, 0),
        'b':    (-1, 1),
        'n':    (1, 1),
        'y':    (-1, -1),
        'u':    (1, -1),
        'x':    (0, 0)
        }
    
    yn_vals = {
        'y':    True,
        'n':    False
        }
    
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        self.stdscr.clear()
        self.game = Game()
        self.grid_size = self.game.grid_size
        self.setup_nonmove_cmds()
        self.setup_windows()
        self.update_grid()
        self.update_info()
        self.stdscr.refresh()
        self.mainloop()
    
    def setup_windows(self):
        x, y, _ = self.grid_size
        self.grid_win = self.stdscr.subwin(y+2, x+2, 0, 0)
        self.grid_win.border()
        # Also add in info grid.
        self.info_win = self.stdscr.subwin(y+2, 20, 0, x+3)
        self.info_win.border()
    
    def setup_nonmove_cmds(self):
        """Here we bind keys to their functions."""
        self.nonmove_cmds = {
            'q':                    self.prompt_quit,
            chr(curses.KEY_NPAGE):  self.view_next_elev,
            chr(curses.KEY_PPAGE):  self.view_prev_elev,
            't':                    self.teleport,
            'p':                    self.zoom_to_player
            }
    
    def update_grid(self):
        grid = self.game.view_grid()
        for row_num, row in enumerate(grid):
            chars = [self.charmap.get(gameclass(ch), ' ') for ch in row]
            self.grid_win.addstr(row_num+1, 1, ''.join(chars))
        self.grid_win.noutrefresh()
    
    def update_info(self):
        self.info_win.erase()
        self.info_win.addstr(1, 1, 'Player coords:')
        self.info_win.addstr(2, 1, '({}, {}, {})'.format(*self.game.player_coords))
        self.info_win.addstr(4, 1, 'Viewing elev:')
        self.info_win.addstr(5, 1, str(self.game.elev))
        self.info_win.addstr(6, 1, 'Level:')
        self.info_win.addstr(7, 1, str(self.game.level))
        self.info_win.addstr(9, 1, 'Enemies:')
        self.info_win.addstr(10, 1, str(self.game.enemy_count))
        self.info_win.noutrefresh()
    
    def mainloop(self):
        while True:
            y, x = reversed(self.game.player_coords[:2])
            cmd_key = chr(self.stdscr.getch(0, 0))
            self.handle_cmd(cmd_key)
            self.stdscr.refresh()

    def handle_cmd(self, cmd):
        if unctrl(cmd).lower() in self.xy_move_keys:
            self.move(cmd)
        elif cmd in self.nonmove_cmds:
            self.nonmove_cmds[cmd]()
        self.update_info()
    
    def move(self, cmd):
        if is_ctrl(cmd):
            z = -1
        elif cmd.isupper():
            z = 1
        else:
            z = 0
        x, y = self.xy_move_keys[unctrl(cmd).lower()]
        try:
            self.game.move_player(x, y, z)
        except GameOver:
            self.on_game_over()
        except LevelComplete:
            self.on_level_complete()
        self.update_grid()
    
    def teleport(self):
        self.game.teleport_player()
        self.update_grid()
    
    def zoom_to_player(self):
        self.game.zoom_to_player()
    
    def view_elev(self, elev):
        if elev in range(self.grid_size[2]):
            self.game.elev = elev
            self.update_grid()
    
    def view_next_elev(self):
        self.view_elev(self.game.elev-1)
    
    def view_prev_elev(self):
        self.view_elev(self.game.elev+1)
    
    def get_yn(self, prompt, default=True):
        prev = self.grid_win.instr(0, 0, len(prompt))
        self.grid_win.addstr(0, 0, prompt)
        ch = chr(self.grid_win.getch(1, 0)).lower()
        return self.yn_vals.get(ch, default)
    
    def on_level_complete(self):
        self.game.next_level()
        self.update_grid()
        self.update_info()

    def on_game_over(self):
        self.quit('You died!')
    
    def prompt_quit(self):
        if self.get_yn('Really quit? (y/N)', False):
            self.quit()

    def quit(self, msg=None, status=0):
        self.stdscr.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        if msg is not None:
            print(msg)
        quit(status)