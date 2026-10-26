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

    def test_speed_bonus_decreases_without_penalty(self):
        times = (0, 1000, 10000, 30000, 120000, 1000000, 100000000)
        bonuses = [maze.speed_bonus(ms) for ms in times]
        self.assertEqual(bonuses[:4], [1000, 909, 500, 250])
        self.assertEqual(bonuses, sorted(bonuses, reverse=True))
        self.assertTrue(all(0 <= bonus <= 1000 for bonus in bonuses))
        self.assertEqual(maze.speed_bonus(-1), 1000)

    def test_separate_bonuses_no_double_award_and_running_total(self):
        game = maze.Maze()
        game.advance(10000)
        for step in route(game, game.player, game.key, locked=True):
            game.move(*step)
        self.assertEqual((game.key_bonus, game.stage_ms, game.score),
                         (500, 0, 500))
        key_pos = game.player
        path = route(game, game.player, game.door)
        game.move(*path[0])
        game.move(-path[0][0], -path[0][1])
        self.assertEqual(game.player, key_pos)
        self.assertEqual(game.score, 500)
        game.advance(30000)
        for step in path:
            game.move(*step)
        self.assertEqual((game.door_bonus, game.score), (250, 750))
        game.move(*path[-1])
        game.advance(50000)
        self.assertEqual((game.score, game.stage_ms), (750, 30000))
        game.new_level()
        self.assertEqual((game.level, game.score, game.stage_ms), (2, 750, 0))
        self.assertEqual((game.key_bonus, game.door_bonus), (0, 0))
        self.assertEqual(maze.Maze().score, 0)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.pressed = set()
        self.held = set()
        self.imu = (0, 0, -16000, 0, 0, 0)
        self.upside_down = False
        self.badge = types.SimpleNamespace(
            ticks_delta=16, mode=Mock(),
            pressed=lambda button: button in self.pressed,
            held=lambda button: button in self.held,
            imu=lambda: self.imu,
            upside_down=lambda: self.upside_down)
        self.screen = Mock(width=160, height=120)
        self.screen.measure_text.side_effect = lambda text: (len(text) * 5, 13)
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
        self.assertEqual(self.namespace["notice"],
                         "KEY +%d" % game.key_bonus)
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

    def test_paused_intro_and_transition_time_excluded_from_bonuses(self):
        game = self.namespace["game"]
        self.frame(ms=5000)
        self.assertEqual(game.stage_ms, 0)
        self.start()
        self.frame(ms=100)
        before_pause = game.stage_ms
        self.frame(pressed=("MENU",), ms=16)
        self.frame(ms=60000)
        self.frame(pressed=("BACK",), ms=1000)
        self.assertEqual(game.stage_ms, before_pause)
        self.frame(ms=100)
        self.assertEqual(game.stage_ms, before_pause + 100)
        game.escaped = True
        self.namespace["escape_ms"] = 1200
        self.frame(ms=1199)
        self.assertEqual(game.stage_ms, before_pause + 100)
        self.frame(ms=1)
        self.assertEqual(game.stage_ms, 0)

    def test_select_toggles_motion_without_changing_intro_or_reset(self):
        self.start()
        self.assertFalse(self.namespace["motion_mode"])
        self.frame(pressed=("SELECT",))
        self.assertTrue(self.namespace["motion_mode"])
        self.assertEqual(self.namespace["notice"], "TILT: HOLD STILL")
        self.frame(pressed=("SELECT",), held=("RIGHT",))
        self.assertFalse(self.namespace["motion_mode"])
        self.assertFalse(self.namespace["repeat"].ready)
        self.frame(pressed=("SELECT",))
        self.frame(pressed=("MENU",))
        self.frame(pressed=("DOWN",))
        self.frame(pressed=("SELECT",))
        self.assertFalse(self.namespace["motion_mode"])
        self.assertEqual(self.namespace["game"].score, 0)

    def test_motion_input_pause_resume_and_orientation_recenter(self):
        self.start()
        self.frame(pressed=("SELECT",))
        game = self.namespace["game"]
        game.move = Mock(return_value="moved")
        for _ in range(20):
            self.frame()
        game.move.assert_not_called()
        self.imu = (6500, 0, -15000, 0, 0, 0)
        for _ in range(30):
            self.frame()
        self.assertTrue(game.move.called)
        self.assertTrue(all(call.args == (1, 0)
                            for call in game.move.call_args_list))
        self.frame(pressed=("MENU",))
        game.move.reset_mock()
        for _ in range(20):
            self.frame()
        game.move.assert_not_called()
        self.frame(pressed=("BACK",))
        for _ in range(20):
            self.frame()
        game.move.assert_not_called()
        self.upside_down = True
        self.frame()
        game.move.assert_not_called()
        self.assertTrue(self.namespace["tilt"].orientation)

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

    def test_bottom_text_keeps_three_pixel_font_bounds_clearance(self):
        labels = ("SELECT: BEGIN", "FIND THE KEY", "FIND THE DOOR",
                  "KEY +1000", "NEED THE KEY", "DOOR +1000", "DUNGEON WORLD")
        for label in labels:
            for height in (13, 15):
                self.screen.measure_text.side_effect = (
                    lambda text, h=height: (len(text) * 5, h))
                self.screen.text.reset_mock()
                self.namespace["footer"](label)
                rendered_label, x, y = self.screen.text.call_args.args
                self.assertEqual(rendered_label, label)
                self.assertEqual(y + height, self.screen.height - 3)
                self.assertGreaterEqual(x, 0)
        self.screen.measure_text.side_effect = lambda text: (len(text) * 5, 13)
        for state in ("intro", "play", "pause"):
            self.namespace["state"] = state
            self.screen.text.reset_mock()
            self.frame()
            for call in self.screen.text.call_args_list:
                label, _, y = call.args
                self.assertLessEqual(y + 13, self.screen.height - 3,
                                     (state, label, y))


class TiltTests(unittest.TestCase):
    def neutral(self, upside_down=False, reading=(0, 0, -16000)):
        tilt = maze.TiltControl()
        tilt.steps(reading, upside_down, 16)
        for _ in range(20):
            self.assertEqual(tilt.steps(reading, upside_down, 16), (None, 0))
        return tilt

    def test_deadzone_and_real_stationary_noise_never_move(self):
        tilt = self.neutral(reading=(-260, -1300, -16000))
        for i in range(200):
            reading = (-260 + (i % 7) * 10, -1300 + (i % 9) * 20,
                       -16000 + (i % 5) * 30)
            self.assertEqual(tilt.steps(reading, False, 16), (None, 0))
        tilt = self.neutral()
        for _ in range(200):
            self.assertEqual(tilt.steps((1000, 1000, -16000), False, 16),
                             (None, 0))

    def test_normalized_axes_and_rotation_mapping(self):
        for scale in (1, 4):
            for upside_down in (False, True):
                for reading, expected in (
                    ((6500, 0, -15000), (1, 0)),
                    ((-6500, 0, -15000), (-1, 0)),
                    ((0, 6500, -15000), (0, 1)),
                    ((0, -6500, -15000), (0, -1)),
                ):
                    tilt = self.neutral(upside_down)
                    outputs = [tilt.steps(
                        tuple(value * scale for value in reading),
                        upside_down, 16) for _ in range(40)]
                    moved = [direction for direction, count in outputs if count]
                    self.assertTrue(moved)
                    if upside_down:
                        expected = (-expected[0], -expected[1])
                    self.assertTrue(all(direction == expected for direction in moved))

    def test_dominant_axis_hysteresis_and_bounded_repeat(self):
        tilt = self.neutral()
        outputs = [tilt.steps((8000, 4000, -14000), False, 20)
                   for _ in range(100)]
        moved = [direction for direction, count in outputs if count]
        self.assertTrue(all(direction == (1, 0) for direction in moved))
        self.assertGreater(len(moved), 5)
        self.assertLess(len(moved), 13)
        self.assertLessEqual(tilt.steps((8000, 0, -14000), False, 5000)[1], 1)
        for _ in range(40):
            result = tilt.steps((0, 0, -16000), False, 20)
        self.assertEqual(result, (None, 0))

    def test_orientation_change_missing_sensor_and_recenter_do_not_jump(self):
        tilt = self.neutral()
        self.assertEqual(tilt.steps((6500, 0, -15000), True, 100), (None, 0))
        for _ in range(30):
            self.assertEqual(tilt.steps((6500, 0, -15000), True, 16), (None, 0))
        self.assertEqual(tilt.steps((0, 0, 0), True, 16), (None, 0))
        self.assertIsNone(tilt.reference)
        self.assertEqual(tilt.steps((0, 0, -16000), True, 16), (None, 0))

    def test_pitch_wrap_is_not_a_full_turn(self):
        tilt = self.neutral(reading=(0, -16000, 20))
        for _ in range(30):
            self.assertEqual(tilt.steps((0, -16000, -20), False, 20),
                             (None, 0))


if __name__ == "__main__":
    unittest.main()
