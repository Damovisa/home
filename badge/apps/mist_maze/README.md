# Mist Maze

Mist Maze is an endless pixel-art memory maze with disappearing terrain and randomly changing forest, dungeon, and ocean worlds.

Use the logical D-pad to walk one tile at a time; hold a direction to keep
walking. Find the gold key, then walk into the white-framed door to escape.
A locked door is impassable until you find the key.

Only tiles within a circular three-tile radius of your character are visible.
Previously seen terrain, keys, and doors disappear completely when you move
away, so remember your route. Vision passes through walls within that radius.
Trees and water block forest paths; dungeon masonry blocks stone paths;
water blocks the ocean's sandy island paths. All themes share the same rules.

Every escape creates a new connected, randomly generated maze and a different
random theme. The level is shown at the top left, your running score in the
center, and the top-right key icon indicates possession, never its location.
The pause screen names the current world. There are no enemies, time limits,
or lives.

## Speed bonuses

Finding the key and reaching the door each award a separate bonus. The key
timer starts when a level begins; the door timer starts when you collect the
key. Each bonus is `floor(1000 * 10 / (10 + seconds))`: for example, 1,000
points immediately, 500 after 10 seconds, or 250 after 30 seconds. Faster is
better, but taking longer never subtracts points or ends the game. Fractional
seconds count, pauses and between-level transitions do not, and there is no
on-screen countdown.

`KEY +...` and `DOOR +...` show each award. Bonuses accumulate across levels;
New Journey resets both the level and the score.

Press Select to begin. Menu or Back pauses and shows Continue / New Journey;
use Up or Down to choose and Select to confirm. Back resumes without changing
the maze. New Journey starts again at level one. Release the D-pad after
starting, resuming, or changing levels before moving. Home belongs to the
badge launcher. Progress is not saved when leaving the app.

## Tilt controls

While playing, press Select to toggle between D-pad and motion mode. Hold
the badge comfortably with the screen facing you and keep it steady as you
enable motion mode: that position becomes neutral. Tilt left/right or tip
the top edge away/toward you to move up/down. Return toward neutral to stop.
Select always returns to D-pad mode without needing to reach a menu.

The letter beside the level is `D` for D-pad or `T` for tilt. Motion input
has smoothing, an approximately 10-degree dead zone, and slower bounded tile
repeat, so small hand tremors do not cause wandering or diagonal moves.
Pausing stops motion. Resuming, changing level, or rotating the badge upside
down re-centers the current holding position to avoid unexpected movement.
New Journey starts in D-pad mode. The simulator can check the mode and
input logic but does not reproduce physical tilt feel.

No extra hardware, network, or secrets are required. The app targets the
Universe 2026 firmware and uses its orientation-aware logical controls.
The bundled `icon.png` is the menu icon; older installed menus may need the
repository's separate custom-icon patch before displaying it.

## Host checks

From the repository root:

```sh
python3 -m unittest discover -s tests -p test_mist_maze.py
python3 .github/skills/hyb26-skill/scripts/validate_app.py badge/apps/mist_maze
```

In the simulator or on the badge, also check the opening screen, D-pad holds,
pause/resume, key pickup, the locked door, speed bonuses, the next world's
reset, tilt mode and re-centering, and inverted orientation. Simulator checks
do not replace physical badge verification.
