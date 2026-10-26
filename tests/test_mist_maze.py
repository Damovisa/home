"""Host-side invariants and runtime integration for the 2026 Mist Maze app."""

import importlib.util
from pathlib import Path
import random
import sys
import types
import unittest
from unittest.mock import Mock, patch


APP = Path(__file__).resolve().parents[1] / "badge/apps/mist_maze"
spec = importlib.util.spec_from_file_location("mist_maze_logic", APP / "maze.py")
maze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maze)


def route(game, start, end, locked=False):
    queue = [start]
    parents = {start: None}
    for x, y in queue:
        if (x, y) == end:
            path = []
            while parents[(x, y)] is not None:
                px, py = parents[(x, y)]
                path.append((x - px, y - py))
                x, y = px, py
            return path[::-1]
        for dx, dy in maze.DIRECTIONS:
            target = x + dx, y + dy
            if (target not in parents and game.walkable(*target)
                    and not (locked and target == game.door)):
                parents[target] = (x, y)
                queue.append(target)
    return None


class MazeTests(unittest.TestCase):
    def test_thousand_random_maps_solve_with_locked_door(self):
        rng = random.getstate()
        try:
            signatures = set()
            themes = set()
            for seed in range(1000):
                random.seed(seed)
                game = maze.Maze()
                signatures.add(b"".join(game.cells))
                themes.add(game.theme)
                self.assertEqual(len({game.player, game.key, game.door}), 3)
                self.assertEqual(sum(sum(row) for row in game.cells), 89)
                self.assertFalse(any(game.cells[0]) or any(game.cells[-1]))
                self.assertTrue(all(not row[0] and not row[-1]
                                    for row in game.cells))
                path = route(game, game.player, game.key, locked=True)
                self.assertIsNotNone(path, seed)
                self.assertGreater(len(path), 8)
                for step in path:
                    result = game.move(*step)
                self.assertEqual(result, "key")
                path = route(game, game.player, game.door)
                self.assertIsNotNone(path, seed)
                for step in path:
                    result = game.move(*step)
                self.assertEqual(result, "escape")
                self.assertTrue(game.has_key and game.escaped)
                self.assertEqual(game.move(1, 0), "blocked")
            self.assertEqual(themes, {0, 1, 2})
            self.assertEqual(len(signatures), 1000)
        finally:
            random.setstate(rng)

    def test_all_floor_is_connected(self):
        game = maze.Maze()
        for y, row in enumerate(game.cells):
            for x, cell in enumerate(row):
                if cell:
                    self.assertIsNotNone(route(game, game.player, (x, y)))

    def test_two_leaf_maze_keeps_locked_door_off_key_route(self):
        with patch.object(maze.random, "randrange", return_value=0):
            game = maze.Maze()
        self.assertEqual(len({game.player, game.key, game.door}), 3)
        path = route(game, game.player, game.key, locked=True)
        self.assertIsNotNone(path)
        for step in path:
            result = game.move(*step)
        self.assertEqual(result, "key")

    def test_collision_invalid_moves_and_key_gate(self):
        game = maze.Maze()
        for step in ((0, 0), (1, 1), (2, 0)):
            before = game.player
            self.assertEqual(game.move(*step), "blocked")
            self.assertEqual(game.player, before)
        for y, row in enumerate(game.cells):
            for x, cell in enumerate(row):
                if cell:
                    for dx, dy in maze.DIRECTIONS:
                        if not game.walkable(x + dx, y + dy):
                            game.player = (x, y)
                            self.assertEqual(game.move(dx, dy), "blocked")
                            self.assertEqual(game.player, (x, y))
        for dx, dy in maze.DIRECTIONS:
            origin = (game.door[0] - dx, game.door[1] - dy)
            if game.walkable(*origin):
                game.player = origin
                self.assertEqual(game.move(dx, dy), "locked")
                self.assertEqual(game.player, origin)
                game.has_key = True
                self.assertEqual(game.move(dx, dy), "escape")
                break

    def test_endless_progression_resets_items_and_changes_theme(self):
        game = maze.Maze()
        for level in range(2, 202):
            previous_theme = game.theme
            game.has_key = game.escaped = True
            game.new_level()
            self.assertEqual(game.level, level)
            self.assertNotEqual(game.theme, previous_theme)
            self.assertFalse(game.has_key or game.escaped)
            self.assertNotEqual(game.player, game.key)
            self.assertNotEqual(game.player, game.door)

    def test_circular_radius_and_no_exploration_memory(self):
        game = maze.Maze()
        game.player = (5, 5)
        for y in range(maze.HEIGHT):
            for x in range(maze.WIDTH):
                self.assertEqual(game.visible(x, y),
                                 (x - 5) ** 2 + (y - 5) ** 2 <= 9)
        self.assertTrue(game.visible(8, 5))
        self.assertFalse(game.visible(8, 6))
        game.player = (12, 5)
        self.assertFalse(game.visible(5, 5))

    def test_repeat_delay_release_direction_and_lag(self):
        repeat = maze.TileRepeat()
        self.assertEqual(repeat.steps((1, 0), 16, True), 0)
        repeat.steps(None, 16)
        self.assertEqual(repeat.steps((1, 0), 16, True), 1)
        self.assertEqual(repeat.steps((1, 0), 259), 0)
        self.assertEqual(repeat.steps((1, 0), 1), 1)
        self.assertEqual(repeat.steps((1, 0), 120), 1)
        self.assertEqual(repeat.steps((0, -1), 16, True), 1)
        self.assertLessEqual(repeat.steps((0, -1), 5000), 4)
        repeat.reset()
        self.assertEqual(repeat.steps((0, -1), 500), 0)
        repeat.steps(None, 0)
        self.assertEqual(repeat.steps((0, -1), 1, True), 1)

    def test_repeat_is_frame_rate_independent(self):
        counts = []
        for frame_ms in (10, 20, 40):
            repeat = maze.TileRepeat()
            repeat.steps(None, 0)
            total = repeat.steps((1, 0), 0, True)
            for _ in range(2000 // frame_ms):
                total += repeat.steps((1, 0), frame_ms)
            counts.append(total)
        self.assertEqual(counts, [16, 16, 16])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.pressed = set()
        self.held = set()
        self.badge = types.SimpleNamespace(
            ticks_delta=16, mode=Mock(),
            pressed=lambda button: button in self.pressed,
            held=lambda button: button in self.held)
        self.screen = Mock(width=160, height=120)
        self.screen.measure_text.side_effect = lambda text: (len(text) * 5, 8)
        self.namespace = {
            "badge": self.badge, "screen": self.screen,
            "font": types.SimpleNamespace(nope=object()),
            "image": types.SimpleNamespace(OFF=0),
            "color": types.SimpleNamespace(rgb=lambda *args: args),
            "LORES": 0, "VSYNC": 1, "run": Mock(),
        }
        for button in ("UP", "DOWN", "LEFT", "RIGHT", "SELECT", "MENU", "BACK"):
            self.namespace["BUTTON_" + button] = button
        fake_os = types.SimpleNamespace(chdir=Mock())
        fake_sys = types.SimpleNamespace(path=[])
        with patch.dict(sys.modules, {"maze": maze, "os": fake_os, "sys": fake_sys}):
            exec(compile((APP / "__init__.py").read_text(),
                         str(APP / "__init__.py"), "exec"), self.namespace)

    def frame(self, pressed=(), held=(), ms=16):
        self.pressed = set(pressed)
        self.held = set(held)
        self.badge.ticks_delta = ms
        self.namespace["update"]()

    def start(self):
        self.frame(pressed=("SELECT",))
        self.frame()

    def test_logical_direction_buttons(self):
        self.start()
        game = self.namespace["game"]
        for button, step in (("UP", (0, -1)), ("DOWN", (0, 1)),
                             ("LEFT", (-1, 0)), ("RIGHT", (1, 0))):
            game.move = Mock(return_value="moved")
            self.frame()
            self.frame(pressed=(button,), held=(button,))
            game.move.assert_called_once_with(*step)
        self.namespace["run"].assert_called_once_with(self.namespace["update"])

    def test_pause_resume_and_new_journey(self):
        self.start()
        game = self.namespace["game"]
        game.level = 8
        self.frame(pressed=("MENU",))
        self.assertEqual(self.namespace["state"], "pause")
        self.frame(pressed=("BACK",))
        self.assertEqual(self.namespace["state"], "play")
        self.assertIs(self.namespace["game"], game)
        self.frame(pressed=("MENU",))
        self.frame(pressed=("DOWN",))
        self.frame(pressed=("SELECT",))
        self.assertEqual(self.namespace["game"].level, 1)
        self.assertIsNot(self.namespace["game"], game)
        self.assertFalse(self.namespace["repeat"].ready)

    def test_progression_and_transition_clears_input(self):
        self.start()
        game = self.namespace["game"]
        old_theme = game.theme
        game.escaped = game.has_key = True
        self.namespace["escape_ms"] = 700
        self.frame(held=("RIGHT",), ms=699)
        self.assertEqual(game.level, 1)
        self.frame(held=("RIGHT",), ms=1)
        self.assertEqual(game.level, 2)
        self.assertNotEqual(game.theme, old_theme)
        self.assertFalse(game.has_key or game.escaped)
        self.assertFalse(self.namespace["repeat"].ready)

    def test_key_pickup_and_locked_door_messages_use_actual_input(self):
        self.start()
        game = self.namespace["game"]
        path = route(game, game.player, game.key, locked=True)
        for step in path[:-1]:
            game.move(*step)
        button_for = {(0, -1): "UP", (0, 1): "DOWN",
                      (-1, 0): "LEFT", (1, 0): "RIGHT"}
        button = button_for[path[-1]]
        self.frame(pressed=(button,), held=(button,))
        self.assertTrue(game.has_key)
        self.assertEqual(self.namespace["notice"], "KEY FOUND!")
        game.has_key = False
        path = route(game, game.player, game.door)
        for step in path[:-1]:
            game.move(*step)
        before = game.player
        button = button_for[path[-1]]
        self.frame()
        self.frame(pressed=(button,), held=(button,))
        self.assertEqual(game.player, before)
        self.assertEqual(self.namespace["notice"], "NEED THE KEY")
        self.assertFalse(game.escaped)

    def test_fog_never_draws_remote_terrain_or_items(self):
        self.start()
        game = self.namespace["game"]
        game.player, game.key, game.door = (1, 1), (17, 9), (15, 9)
        self.namespace["draw_tile"] = Mock()
        self.namespace["draw_key"] = Mock()
        self.namespace["draw_door"] = Mock()
        self.namespace["draw_world"]()
        drawn = {(call.args[2], call.args[3])
                 for call in self.namespace["draw_tile"].call_args_list}
        expected = {(x, y) for y in range(maze.HEIGHT)
                    for x in range(maze.WIDTH) if game.visible(x, y)}
        self.assertEqual(drawn, expected)
        self.namespace["draw_key"].assert_not_called()
        self.namespace["draw_door"].assert_not_called()
        game.player = (17, 8)
        self.namespace["draw_tile"].reset_mock()
        self.namespace["draw_world"]()
        self.namespace["draw_key"].assert_called_once()
        self.namespace["draw_door"].assert_called_once()
        self.assertNotIn((1, 1), {(c.args[2], c.args[3])
                                 for c in self.namespace["draw_tile"].call_args_list})


if __name__ == "__main__":
    unittest.main()
