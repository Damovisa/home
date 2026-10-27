import os
import sys

APP_DIR = "/system/apps/mist_maze"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from maze import Maze, TileRepeat, TiltControl, WIDTH, HEIGHT, THEMES

badge.mode(LORES | VSYNC)
screen.font = font.nope
screen.antialias = image.OFF

INK = color.rgb(8, 13, 23)
WHITE = color.rgb(239, 246, 222)
GOLD = color.rgb(255, 211, 89)
MUTED = color.rgb(139, 158, 163)
PALETTES = (
    (color.rgb(53, 91, 56), color.rgb(87, 125, 65),
     color.rgb(22, 53, 45), color.rgb(42, 91, 58),
     color.rgb(35, 75, 96), color.rgb(68, 118, 137)),
    (color.rgb(72, 66, 80), color.rgb(101, 91, 107),
     color.rgb(33, 31, 48), color.rgb(64, 57, 78),
     color.rgb(33, 31, 48), color.rgb(64, 57, 78)),
    (color.rgb(183, 152, 94), color.rgb(214, 189, 121),
     color.rgb(20, 66, 88), color.rgb(44, 104, 126),
     color.rgb(20, 66, 88), color.rgb(44, 104, 126)),
)
BUTTONS = ((BUTTON_UP, (0, -1)), (BUTTON_DOWN, (0, 1)),
           (BUTTON_LEFT, (-1, 0)), (BUTTON_RIGHT, (1, 0)))

game = Maze()
repeat = TileRepeat()
tilt = TiltControl()
motion_mode = False
state = "intro"
menu_choice = 0
notice = ""
notice_ms = 0
escape_ms = 0


def box(x, y, w, h, pen):
    screen.pen = pen
    screen.rectangle(x, y, w, h)


def text(label, x, y, pen=WHITE):
    screen.pen = pen
    screen.text(label, x, y)


def centered(label, y, pen=WHITE):
    width, _ = screen.measure_text(label)
    text(label, (screen.width - width) // 2, y, pen)


def footer(label, pen=WHITE):
    _, height = screen.measure_text(label)
    centered(label, screen.height - height - 3, pen)


def bonus_label():
    return "%s +%d" % (
        "EXIT" if game.has_key else "KEY", game.available_bonus())


def draw_key(x, y):
    box(x + 1, y + 1, 4, 4, INK)
    box(x + 1, y, 3, 3, GOLD)
    box(x + 2, y + 1, 1, 1, INK)
    box(x + 3, y + 3, 3, 2, GOLD)
    box(x + 5, y + 4, 1, 3, GOLD)
    box(x + 4, y + 5, 2, 1, GOLD)


def draw_door(x, y):
    box(x + 1, y, 6, 8, INK)
    box(x + 2, y, 4, 1, WHITE)
    box(x + 1, y + 1, 1, 7, WHITE)
    box(x + 6, y + 1, 1, 7, WHITE)
    if game.has_key:
        box(x + 2, y + 1, 4, 7, color.rgb(74, 161, 133))
    else:
        box(x + 2, y + 2, 4, 5, color.rgb(127, 79, 54))
        box(x + 4, y + 4, 1, 2, GOLD)


def draw_player(x, y):
    box(x + 1, y + 6, 6, 2, INK)
    box(x + 2, y, 4, 2, color.rgb(224, 107, 72))
    box(x + 1, y + 1, 6, 1, color.rgb(248, 148, 83))
    box(x + 2, y + 2, 4, 3, WHITE)
    box(x + 4, y + 3, 1, 1, INK)
    box(x + 2, y + 5, 4, 2, color.rgb(113, 197, 197))
    box(x + 2, y + 7, 1, 1, WHITE)
    box(x + 5, y + 7, 1, 1, WHITE)


def draw_tile(x, y, gx, gy):
    floor, detail, wall, highlight, water, ripple = PALETTES[game.theme]
    variant = (gx * 17 + gy * 31) % 7
    if game.cells[gy][gx]:
        box(x, y, 8, 8, floor)
        box(x + 1 + variant % 3, y + 2, 1, 1, detail)
        box(x + 5, y + 6, 2, 1, detail)
    elif game.theme == 2 or (game.theme == 0 and variant < 2):
        box(x, y, 8, 8, water)
        box(x + 1, y + 2, 3, 1, ripple)
        box(x + 4, y + 5, 3, 1, ripple)
    elif game.theme == 0:
        box(x, y, 8, 8, wall)
        box(x + 3, y + 5, 2, 3, color.rgb(104, 78, 48))
        box(x + 2, y + 1, 4, 4, highlight)
        box(x + 1, y + 3, 6, 3, highlight)
        box(x + 3, y + 1, 2, 2, detail)
    else:
        box(x, y, 8, 8, wall)
        box(x, y, 8, 1, highlight)
        box(x, y + 4, 8, 1, highlight)
        box(x + 3, y, 1, 4, highlight)
        box(x + 6, y + 4, 1, 4, highlight)


def draw_world():
    left = (screen.width - WIDTH * 8) // 2
    top = 18
    text("%02d%s" % (game.level, "T" if motion_mode else "D"), 4, 3, GOLD)
    centered("S:%d" % game.score, 3, WHITE)
    if game.has_key:
        draw_key(screen.width - 12, 4)
    else:
        text("--", screen.width - 16, 3, MUTED)
    box(4, 16, screen.width - 8, 1, color.rgb(35, 47, 55))
    # No explored map is retained: terrain and items are drawn only in sight.
    for gy in range(max(0, game.player[1] - 3),
                    min(HEIGHT, game.player[1] + 4)):
        for gx in range(max(0, game.player[0] - 3),
                        min(WIDTH, game.player[0] + 4)):
            if not game.visible(gx, gy):
                continue
            x, y = left + gx * 8, top + gy * 8
            draw_tile(x, y, gx, gy)
            if (gx, gy) == game.key and not game.has_key:
                draw_key(x, y)
            if (gx, gy) == game.door:
                draw_door(x, y)
    draw_player(left + game.player[0] * 8, top + game.player[1] * 8)
    label = notice if notice_ms > 0 else bonus_label()
    footer(label, GOLD if notice_ms > 0 else MUTED)


def draw_intro():
    centered("MIST MAZE", 15, GOLD)
    draw_player(screen.width // 2 - 22, 35)
    draw_key(screen.width // 2 - 3, 35)
    draw_door(screen.width // 2 + 16, 35)
    centered("Find key. Find door.", 53)
    centered("Only 3 tiles in sight.", 66, MUTED)
    centered("The rest disappears.", 77, MUTED)
    centered("Faster = more points", 91)
    footer("SELECT: BEGIN", GOLD)


def update():
    global state, menu_choice, notice, notice_ms, escape_ms, game, motion_mode
    elapsed = max(0, badge.ticks_delta)
    box(0, 0, screen.width, screen.height, INK)
    if state == "intro":
        draw_intro()
        if badge.pressed(BUTTON_SELECT):
            state = "play"
            repeat.reset()
        return
    if state == "pause":
        centered("TAKE A BREATH", 22, GOLD)
        centered("Nothing is chasing you.", 40, MUTED)
        centered("%s / %s" % (
            THEMES[game.theme], "TILT" if motion_mode else "D-PAD"), 56, MUTED)
        if badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
            menu_choice = 1 - menu_choice
        centered("> CONTINUE" if menu_choice == 0 else "CONTINUE",
                 75, GOLD if menu_choice == 0 else WHITE)
        centered("> NEW JOURNEY" if menu_choice == 1 else "NEW JOURNEY",
                 91, GOLD if menu_choice == 1 else WHITE)
        footer(bonus_label(), MUTED)
        if badge.pressed(BUTTON_BACK) or badge.pressed(BUTTON_MENU):
            state = "play"
            repeat.reset()
            tilt.reset()
        elif badge.pressed(BUTTON_SELECT):
            if menu_choice:
                game = Maze()
                notice_ms = 0
                escape_ms = 0
                motion_mode = False
            state = "play"
            repeat.reset()
            tilt.reset()
        return
    notice_ms = max(0, notice_ms - elapsed)
    if game.escaped:
        escape_ms -= elapsed
        if escape_ms <= 0:
            game.new_level()
            notice = THEMES[game.theme] + " WORLD"
            notice_ms = 1200
            repeat.reset()
            tilt.reset()
    elif badge.pressed(BUTTON_MENU) or badge.pressed(BUTTON_BACK):
        state = "pause"
        menu_choice = 0
        repeat.reset()
        tilt.reset()
    elif badge.pressed(BUTTON_SELECT):
        game.advance(elapsed)
        motion_mode = not motion_mode
        repeat.reset()
        tilt.reset()
        if motion_mode:
            tilt.steps(badge.imu(), badge.upside_down(), 0)
        notice = "TILT: HOLD STILL" if motion_mode else "D-PAD MODE"
        notice_ms = 1200
    else:
        game.advance(elapsed)
        direction = None
        pressed = False
        if motion_mode:
            direction, count = tilt.steps(
                badge.imu(), badge.upside_down(), elapsed)
            if tilt.reference is None:
                notice, notice_ms = "WAIT FOR IMU", 100
        else:
            for button, delta in BUTTONS:
                if badge.pressed(button):
                    direction = delta
                    pressed = True
                    break
            if direction is None:
                for button, delta in BUTTONS:
                    if badge.held(button):
                        direction = delta
                        break
            count = repeat.steps(direction, elapsed, pressed)
        for _ in range(count):
            result = game.move(*direction)
            if result == "key":
                notice, notice_ms = "KEY BANKED +%d" % game.key_bonus, 1200
                break
            elif result == "locked":
                notice, notice_ms = "NEED THE KEY", 900
                break
            elif result == "escape":
                notice, notice_ms = "EXIT BANKED +%d" % game.door_bonus, 1200
                escape_ms = 1200
                break
            elif result == "blocked":
                break
    draw_world()


run(update)
