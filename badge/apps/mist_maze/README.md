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
random theme. The level is shown at the top left; the top-right key icon
indicates possession, never the key's location. There are no enemies, timers,
or lives.

Press Select to begin. Menu or Back pauses and shows Continue / New Journey;
use Up or Down to choose and Select to confirm. Back resumes without changing
the maze. New Journey starts again at level one. Release the D-pad after
starting, resuming, or changing levels before moving. Home belongs to the
badge launcher. Progress is not saved when leaving the app.

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
pause/resume, key pickup, the locked door, the next world's reset, and inverted
orientation. Simulator checks do not replace physical badge verification.
