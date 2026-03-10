# Session Notes

## Current State

- Project root: `G:\Billiard`
- Main work is in `main.py`
- Last committed branch state before current uncommitted edits: `main` is ahead of `origin/main` by 3 commits
- Current working tree has uncommitted changes in `main.py`

## Implemented So Far

- Restored runnable Pygame MVP
- Added `requirements.txt` and `README.md`
- Refactored the game loop into clearer sections
- Added round end states with restart by `R`
- Tuned shot control and basic physics
- Switched table geometry to millimeters with render scaling
- Replaced circular pocket approximation with corridor-based pocket logic
- Updated initial layout to 16 balls:
  - black ball `0` in the center of one half of the table
  - white balls `1..15` in a pyramid on the other half

## Confirmed Geometry

- Playfield size: `3657.6 x 1828.8 mm`
- Ball diameter: `68 mm`
- Corner pocket corridor: `73 mm` width, `15 mm` depth
- Side pocket corridor on long rail: `90 mm` width, `0 mm` depth

## Important Current Limitation

- Rules of `Американка` are not implemented yet
- The code still behaves like a simplified single-active-cue flow
- "Any ball can be the cue ball" is not implemented yet
- Two-player turn handling is not implemented yet
- Foul penalty ball re-spotting by the agreed rule is not implemented yet

## Next Step

Implement the actual `Американка` turn model:

- 2 players
- before each shot, player selects any ball on the table as the cue ball
- any pocketed ball counts for the current player
- if at least one ball is pocketed, the player continues the series
- if no ball is pocketed, turn passes
- foul if the selected cue ball does not touch any other ball
- foul penalty: return one previously pocketed ball of that player to the table if possible

## Resume Prompt

Use this when resuming:

`Continue Billiard from SESSION_NOTES.md. Next task: implement 2-player American pyramid turn rules with selectable cue ball.`
