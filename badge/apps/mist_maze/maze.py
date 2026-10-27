"""Connected mazes and frame-rate-independent tile input."""

import random
import math

WIDTH = 19
HEIGHT = 11
RADIUS = 3
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))
THEMES = ("FOREST", "DUNGEON", "OCEAN")


def speed_bonus(elapsed_ms):
    return 10000000 // (10000 + max(0, elapsed_ms))


class Maze:
    def __init__(self):
        self.level = 0
        self.score = 0
        self.theme = random.randrange(len(THEMES))
        self.new_level()

    def new_level(self):
        if self.level:
            # Vary the world without a predictable rotation or immediate repeat.
            self.theme = (self.theme + 1 + random.randrange(2)) % len(THEMES)
        self.level += 1
        self.cells = [bytearray(WIDTH) for _ in range(HEIGHT)]
        self.player = (1 + 2 * random.randrange(WIDTH // 2),
                       1 + 2 * random.randrange(HEIGHT // 2))
        stack = [self.player]
        self.cells[self.player[1]][self.player[0]] = 1
        while stack:
            x, y = stack[-1]
            choices = []
            for dx, dy in DIRECTIONS:
                nx, ny = x + dx * 2, y + dy * 2
                if (0 < nx < WIDTH - 1 and 0 < ny < HEIGHT - 1
                        and not self.cells[ny][nx]):
                    choices.append((dx, dy, nx, ny))
            if not choices:
                stack.pop()
                continue
            dx, dy, nx, ny = choices[random.randrange(len(choices))]
            self.cells[y + dy][x + dx] = 1
            self.cells[ny][nx] = 1
            stack.append((nx, ny))
        self.key = self.farthest(self.player, ())
        # A leaf door cannot cut off the key while locked.
        leaves = set()
        for y in range(1, HEIGHT - 1):
            for x in range(1, WIDTH - 1):
                if self.cells[y][x] and sum(
                    self.walkable(x + dx, y + dy) for dx, dy in DIRECTIONS
                ) == 1:
                    leaves.add((x, y))
        self.door = self.farthest(
            self.key, (self.player, self.key), leaves)
        if self.door == self.key:
            # A two-leaf maze uses the original spawn as its door.
            self.door = self.player
            x, y = self.player
            for dx, dy in DIRECTIONS:
                if self.walkable(x + dx, y + dy):
                    self.player = (x + dx, y + dy)
                    break
        self.has_key = False
        self.escaped = False
        self.stage_ms = 0
        self.key_bonus = 0
        self.door_bonus = 0

    def advance(self, elapsed_ms):
        if not self.escaped:
            self.stage_ms += max(0, elapsed_ms)

    def available_bonus(self):
        return speed_bonus(self.stage_ms)

    def farthest(self, origin, excluded, candidates=None):
        queue = [origin]
        seen = {origin}
        index = 0
        result = origin
        while index < len(queue):
            x, y = queue[index]
            index += 1
            if ((x, y) not in excluded
                    and (candidates is None or (x, y) in candidates)):
                result = (x, y)
            for dx, dy in DIRECTIONS:
                target = (x + dx, y + dy)
                if target not in seen and self.walkable(*target):
                    seen.add(target)
                    queue.append(target)
        return result

    def walkable(self, x, y):
        return 0 <= x < WIDTH and 0 <= y < HEIGHT and bool(self.cells[y][x])

    def visible(self, x, y):
        dx, dy = x - self.player[0], y - self.player[1]
        return dx * dx + dy * dy <= RADIUS * RADIUS

    def move(self, dx, dy):
        if self.escaped or (dx, dy) not in DIRECTIONS:
            return "blocked"
        target = (self.player[0] + dx, self.player[1] + dy)
        if not self.walkable(*target):
            return "blocked"
        if target == self.door and not self.has_key:
            return "locked"
        self.player = target
        if target == self.key and not self.has_key:
            self.has_key = True
            self.key_bonus = self.available_bonus()
            self.score += self.key_bonus
            self.stage_ms = 0
            return "key"
        if target == self.door:
            self.escaped = True
            self.door_bonus = self.available_bonus()
            self.score += self.door_bonus
            return "escape"
        return "moved"


class TileRepeat:
    DELAY = 260
    INTERVAL = 120

    def __init__(self, delay=DELAY, interval=INTERVAL):
        self.delay = delay
        self.interval = interval
        self.reset()

    def reset(self):
        self.direction = None
        self.remaining = 0
        self.ready = False

    def steps(self, direction, elapsed, pressed=False):
        # Require a release after menus and level changes.
        if direction is None:
            self.ready = True
            self.direction = None
            self.remaining = 0
            return 0
        if not self.ready:
            return 0
        if pressed or direction != self.direction:
            self.direction = direction
            self.remaining = self.delay
            return 1
        self.remaining -= max(0, min(elapsed, 500))
        count = 0
        while self.remaining <= 0 and count < 4:
            count += 1
            self.remaining += self.interval
        return count


class TiltControl:
    DEAD_ZONE = 0.18
    RELEASE_ZONE = 0.12
    SMOOTH_MS = 90
    SETTLE_MS = 200

    def __init__(self):
        self.repeat = TileRepeat(320, 180)
        self.reset()

    def reset(self):
        self.reference = None
        self.orientation = None
        self.x = self.y = 0.0
        self.settle_ms = self.SETTLE_MS
        self.repeat.reset()

    def steps(self, reading, upside_down, elapsed_ms):
        ax, ay, az = reading[:3]
        magnitude = math.sqrt(ax * ax + ay * ay + az * az)
        if not magnitude:
            self.reset()
            return None, 0
        # Same normalized roll/pitch convention as Mona Paint, independent
        # of the firmware's raw acceleration scale.
        side = math.asin(max(-1.0, min(1.0, ax / magnitude)))
        fore = math.atan2(az, ay)
        if self.reference is None or self.orientation != upside_down:
            self.reset()
            self.reference = (side, fore)
            self.orientation = upside_down
            self.repeat.steps(None, 0)
            return None, 0
        sign = -1 if upside_down else 1
        target_x = (side - self.reference[0]) * sign
        target_y = ((fore - self.reference[1] + math.pi)
                    % (2 * math.pi) - math.pi) * sign
        dt = max(0, min(elapsed_ms, 250))
        blend = 1 - math.exp(-dt / self.SMOOTH_MS)
        self.x += (target_x - self.x) * blend
        self.y += (target_y - self.y) * blend
        if self.settle_ms > 0:
            self.settle_ms -= dt
            return None, 0
        direction = None
        if max(abs(self.x), abs(self.y)) >= self.DEAD_ZONE:
            if abs(self.x) >= abs(self.y):
                direction = (1 if self.x > 0 else -1, 0)
            else:
                direction = (0, 1 if self.y > 0 else -1)
        elif self.repeat.direction is not None:
            dx, dy = self.repeat.direction
            if self.x * dx + self.y * dy >= self.RELEASE_ZONE:
                direction = self.repeat.direction
        return direction, min(1, self.repeat.steps(direction, dt))
