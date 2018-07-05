# Lasers
Summer 2018 puzzle games project

This project is largely based on a game that I created in PuzzleScript, one version of which can be found here: https://www.puzzlescript.net/editor.html?hack=e559af178f5d63b65989cbef2e5fe663

## lasers_progressions.py
This is the main focus of this repo. It stores some data about some of the levels in the game linked above, as well as which other levels each level uses concepts from. This script's purpose is to generate level progressions for this game such that each level only uses concepts from earlier levels, while offering as much flexibility as possible as to the selection and ordering of those levels without breaking that criterion.

It's a work in progress as of the time of this writing, but ultimately I hope to expose the full functionality of this script to its command line arguments.

## timestamper.py 
This is a simple script that takes input from stdin and copies that input to stdout along with the exact time between when the script was started to when each line of input was recieved. We intend to use this to record some notes while people are playing the game, and use the timestamps to match the notes up with a screen recording. I recommend redirecting its output to a file: `python timestamper.py > log.txt`

## lasers_core.txt
This file contains all of the sourcecode for the PuzzleScript game, except for the levels. Some of the functions in lasers_progressions.py read this file to generate fully playable versions of the game.
