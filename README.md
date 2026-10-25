# CrossRepo

[![CI](https://github.com/sgbd0/crossrepo/actions/workflows/ci.yml/badge.svg)](https://github.com/sgbd0/crossrepo/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Turn any codebase into a crossword puzzle.**

CrossRepo scans a repository, mines its real identifiers - classes, functions,
modules, constants - and weaves them into a crossword whose clues come from
your own code: file paths, docstrings, and reference counts. Every answer is a
name your team types every day.

Zero dependencies. Python 3.10+ standard library only.

## Why

New joiners read the docs, skim the tree, and still can't name the five
classes they will touch every day. A crossword built from the repository's own
vocabulary is a ten-minute team ritual that makes those names stick - and a
reliable icebreaker for hackathons and offsites. Rerun it on CI each week and
the puzzle evolves with the code.

## Demo

Real output of CrossRepo scanning **itself** (`crossrepo . --seed 7`):

```
###################################################### 1 ############
################## 2 ### 3  .  4  . ############ 5 ### . ############
######### 6  .  .  .  . ###### . ######### 7 ### . ### . ############
################## . ######### 8  .  9  .  .  .  .  .  . ############
################## . ######### . ### . ### . ### . ### . ############
#########10  .  .  .  . ###### . ### . ### . ### . ### . ######11 ###
################## . ######### . ### . ### . ### . ### . ###### . ###
################## . ############12 ###### . ### . ### . ###### . ###
############13  .  .  .  .  .  .  .  .  .  .  .  .  .  . ###### . ###
############ . ### . ############ . ############ . ######14 ### . ###
###15  .  .  . ######16  .  .  .  .  .  .  .  .  . ###### . ### . ###
############ . ################## . ###############17 ### . ### . ###
18  .  .  .  .  .  .  . ###19  .  .  .  .  .  .  .  .  .  .  .  .  . 
############ . ################## . ############### . ### . ### . ###
############ . ######20 ######### . ############### . ### . #########
###21  .  .  .  . ### . ######22  .  .  .  . ###### . ### . #########
############ . ###### . ######### . ############### . ### . #########
###23  .  .  .  .  .  .  .  .  .  .  . 24  .  . ### . ### . #########
############ . ###### . ######### . ### . ######### . ###############
25  .  .  .  .  .  .  .  .  .  .  . ### . ###26  .  .  . ############
############ . ################## . ### . ######### . ###############
############ . ################## . ### . ###########################
###27  .  .  .  .  .  .  .  . ######### . ###########################

Across
    3. An identifier from this repo: 4 letters, starting with 'W' [4]
    6. Referenced 24 times across this repository [5]
    8. A function defined in src/crossrepo/words.py [9]
   13. A class defined in tests/test_render.py [15]
   ...

Down
    1. A class defined in tests/test_clues.py [9]
    5. A class defined in tests/test_layout.py [10]
   12. A class defined in tests/test_render.py [15]
   24. Class described as 'One named thing found in the repository.'
       (in src/crossrepo/scan.py) [6]
```

The same puzzle as a self-contained, offline HTML file with a typeable grid,
clue highlighting, and Check / Reveal buttons: [examples/demo.html](examples/demo.html).
Full text and JSON exports live in [examples/](examples/).

## Install

```bash
pip install .
crossrepo                 # scans the current directory
```

Or run straight from a checkout without installing:

```bash
PYTHONPATH=src python -m crossrepo path/to/repo
```

## Usage

```text
crossrepo [ROOT] [options]

--words N      how many candidate identifiers to mine (default 24)
--seed N       seed for a reproducible puzzle (default 0)
--reveal       print the filled grid instead of the blank one
--stats        only print repository statistics
--title TEXT   puzzle title (default: '<repo name> - a crossword')
--txt PATH     write the text puzzle to a file instead of stdout
--html PATH    also write a standalone interactive HTML puzzle
--json PATH    also write a JSON export
```

Same seed in, same puzzle out - share a seed instead of a file.

## How it works

1. **Harvest** - walks the tree, skipping `.git`, `node_modules`, caches and
   other noise. Python files are parsed with `ast` for exact symbols; a
   repository without any Python falls back to a language-agnostic tokenizer,
   so any codebase still produces a puzzle.
2. **Mine words** - ranks identifiers by kind and reference count, adds the
   repository name, and splits compound names into fragments
   (`layout_engine` also yields `LAYOUT` and `ENGINE`).
3. **Write clues** - every answer gets a clue derived from real facts: where
   it is defined, what its docstring says, how often it is referenced. A leak
   filter rewrites any clue that would give the answer away.
4. **Weave the grid** - a greedy engine crosses words to maximize
   intersections and compactness while enforcing one invariant: *every
   maximal run of letters must exactly be a placed word.* That single rule
   bans accidental merges (`CAR` next to `ARTS` would spell `CART`) and
   stacking a short word inside a longer one. Standard crossword numbering
   falls out of the same pass.

## The three outputs

| Format | What you get |
| --- | --- |
| text | numbered blank grid plus Across/Down clue lists, ASCII-safe everywhere |
| html | one offline file: typeable grid, clue highlighting, Check and Reveal |
| json | full puzzle data - `answer`, `clue`, `number`, `row`, `col`, `direction` - for your own renderer |

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Ideas welcome

- PDF / PNG export for print handouts
- tree-sitter language plugins beyond the Python/generic pair
- difficulty scoring (intersections per word, clue hardness)
- a GitHub Action that posts a weekly puzzle of your repository

## License

MIT - see [LICENSE](LICENSE).
