"""
A script to generate level progressions for the Lasers game.

The layouts of and dependency relations between a selection of levels are hardcoded into this script.
At the moment, the script basically just provides a collection of tools for ordering the levels in a progression,
but in the future I hope to grant access to those tools from the command line.
"""

from collections import deque
from operator import itemgetter, attrgetter
import pyperclip

def compose(*funcs):
    """ Composes a series of functions, like the Haskell . operator.

    Args:
        *funcs: An arbitrary number of functions to be composed.

    Returns:
        A function that accepts whatever parameters funcs[-1] does, feeds those to funcs[-1],
        feeds the result of that into funcs[-2], etc, all the way through funcs[0], and then
        returns whatever funcs[0] returned.

    >>> add1 = lambda n: n + 1
    >>> times2 = lambda n: n * 2
    >>> add3 = lambda n: n + 3
    >>> f = compose(add1, times2, add3)
    >>> f(4)
    15
    """
    def inner(*a, **kw):
        acc = funcs[-1](*a, **kw)
        for f in funcs[-2::-1]:
            acc = f(acc)
        return acc
    return inner

def takeall(levels, **_):
    return levels

def takeall_reversed(levels, **_):
    return list(reversed(levels))

def takefirst(levels, **_):
    return levels[0:1]

def frontload(levels, **_):
    return sorted(levels, key=attrgetter('usages'), reverse=True)

def backload(levels, **_):
    return sorted(levels, key=attrgetter('usages'))

def takenone(levels, **_):
    return ()

def remove_newlines(s):
    return s.replace('\n', '')

def smaller_first(levels, **kw):
    return sorted(levels, key=compose(len, remove_newlines, attrgetter('layout')))

def larger_first(levels, **kw):
    return sorted(levels, key=compose(len, remove_newlines, attrgetter('layout')), reverse=True)

allLevels = []

def clearUsages():
    for elem in allLevels:
        elem.usages = 0

class Level:
    """ A class representing a Lasers level.

    Attributes:
        name: The name of the level. Mostly for use by level designers.
        layout: The ASCII-art-like Unicode string used to define the level in PuzzleScript.
        deps: A tuple of Levels and Objectives that introduce the gameplay concepts the Level uses.
        usages: An integer used internally by gen_progressions, counting the number of paths from the level at the root of the progression to this level.
            Messing with this could cause problems. Functions that use it are not thread-safe.
    """
    def __init__(self, name, layout, *deps, secret=False):
        """ Initializes a new Level object.

        Args:
            name: A string, representing the name of the level. This won't usually be shown to players.
            layout: The layout of the level, in Puzzlescript's ASCII-art-like syntax. See the link in README.md for examples of how Lasers interprets
                this syntax, and click the "Level Editor" link at the top for assistance in creating syntactically-valid levels.
            *deps: A variable number of Level and Objective objects, each representing a concept that this Level uses.
            secret: If true, this Level will not be automatically appended to the global allLevels list.
                Good for levels intended to only be used as test cases, etc.
        """
        self.name = name
        self.layout = layout
        self.deps = deps
        self.usages = 0
        if not secret:
            allLevels.append(self)

    def flatten(self, *_, **__):
        return [self]

    def flat_deps(self, obj_heuristic=takefirst):
        l = []
        for dep in self.deps:
            l.extend(dep.flatten(obj_heuristic))
        return l

    def progression(self, level_heuristic=takeall, obj_heuristic=takefirst):
        """ Generates a level progression based on this Level, following all the same rules as gen_progressions below.

        Args:
            level_heuristic: The heuristic filtering/sorting function to be invoked on the deps of this and all other Level objects in the progression.
            obj_heuristic: The heuristic iltering/sorting function to be invoked on the opts of all Objective objects in the progression.

        Returns:
            A deque containing a progression of Levels (and no duplicates) ending with this Level.

        Raises:
            RecursionError: There is a dependency loop somewhere in the progression.
        """
        prog = deque()
        prog.append(self)
        for dep in reversed(level_heuristic(self.flat_deps(obj_heuristic))):
            depprog = dep.progression(level_heuristic, obj_heuristic)
            while len(depprog) > 0:
                level = depprog.pop()
                try:
                    prog.remove(level)
                except ValueError:
                    pass
                prog.appendleft(level)
        return prog

    def calcUsages(self, level_heuristic=takeall, obj_heuristic=takefirst):
        """ Recursively computes the usage data for each Level and Objective in this Level's dependencies.

        Args:
            level_heuristic: How the deps of this level and each other level in the progression should be filtered.
                There's really not a good reason to use anything other than the default takeall, as far as I know.
            obj_heuristic: How the opts of each Objective in the progression should be filtered. Should be a superset of
                the objects returned by the obj_heuristic parameter of a subsequent call to self.progression().
        """
        for elem in level_heuristic(self.deps, obj_heuristic=obj_heuristic):
            elem.usages += 1
            elem.calcUsages(level_heuristic, obj_heuristic)

    def __str__(self):
        if len(self.deps) > 0:
            s = ""
            for elem in self.deps:
                s += str(elem) + ", "
            return self.name + " <- [" + s[0:-2] + "]"
        else:
            return self.name

class Objective:
    """ A class representing an abstract concept that appears in Lasers gameplay and/or level design.

    Attributes:
        opts: A tuple of Levels and Objectives that could each be used to introduce the abstract concept this Objective represents.
        usages: An integer used internally by gen_progressions, counting the number of paths from the level at the root of the progression to this objective.
            Messing with this could cause problems. Functions that use it are not thread-safe.
    """
    def __init__(self, *opts):
        """ Initializes a new Objective object.

        Args:
            *opts: A variable number of Level and Objective objects that could each be used to introduce the concept that this Objective's concept.
        """
        self.opts = opts
        self.usages = 0
        allLevels.append(self)

    def flatten(self, obj_heuristic=takefirst):
        l = []
        for opt in self.opts:
            l.extend(opt.flatten(obj_heuristic))
        return obj_heuristic(l)

    def progression(self, level_heuristic=takeall, obj_heuristic=takefirst):
        """ Generates a progression for each of this Objective's opts, and strings them all together.

        Unlike Level.progression() and gen_progression() (which calls Level.progression()), this method DOES NOT ensure that the returned deque
        does not contain any duplicate levels. It simply calls .progression() on each object returned by obj_heuristic(self.opts), and concatenates
        them all together. If obj_heuristic is the default takefirst or otherwise only returns one object from its argument, then this method will
        simply return that selected object's progression, which will in that case not have any duplicate entries; but if obj_heuristic can return
        multiple elements, this method can and usually will return duplicates.

        Args:
            level_heuristic: A function that determines how the deps of the Levels in the progression should be filtered and sorted. Does not apply to
                this or other Objective objects, except by way of any of the Objective's opts that happen to be Levels.
            obj_heuristic: A function that determines which opts' progressions should appear in the output sequence, and the order in which those
                progressions should appear. Also applies in the same way to any other Objective objects encoutered while generating those progressions.

        Returns:
            A deque containing this Objective's recursively expanded dependencies, as described above.
        """
        print('Warning: Objective.progression() is now deprecated')
        prog = deque()
        for elem in obj_heuristic(self.opts, obj_heuristic=obj_heuristic):
            prog.extend(elem.progression(level_heuristic, obj_heuristic))
        return prog

    def calcUsages(self, level_heuristic=takeall, obj_heuristic=takefirst):
        """ Recursively computes the usage data for this Objective's opts in much the same way as Level.calcUsages().

        Args:
            level_heuristic: How the deps of the Levels in the progression should be filtered.
                There's really not a good reason to use anything other than the default takeall, as far as I know.
            obj_heuristic: How the opts of this and other Objectives in the progression should be filtered. Should be a superset of
                the objects returned by the obj_heuristic parameter of a subsequent call to self.progression().
        """
        for elem in obj_heuristic(self.opts, obj_heuristic=obj_heuristic):
            elem.usages += 1
            elem.calcUsages(level_heuristic, obj_heuristic)

    def __str__(self):
        s = ""
        for elem in self.opts:
            s += str(elem) + " or "
        return "(" + s[0:-4] + ")"

#WARNING: Don't use heuristics that filter the list based on usages for the usage_* parameters.
# They're used to generate the usage info, so if they also depend on the usage info, it'll cause problems.
# frontload and backload work fine as usage_* params, though, since calcUsages() doesn't care about the order of the levels that the heuristic returns.
def gen_progression(level, level_heuristic=takeall, obj_heuristic=takefirst, usage_level_heuristic=takeall, usage_obj_heuristic=takeall):
    """ Takes a Level and a set of heuristics, and generates a level progression that tries to follow the heuristics,
    but ensures that each level in the progression only uses concepts introduced earlier in the progression.

    Args:
        level: The Level object to generate a progression from. The generated progression will include all levels that this level
            borrows concepts from, as filtered by the heuristics, and only those levels. As such, this level will always
            be placed at the end of the progression.
        level_heuristic: How the deps of each Level in the progression should be filtered and ordered. Should be a function that
            takes a sequence (typically a tuple) as an argument and returns another sequence (such as a tuple or list).
            Usually, you'll want this one to return a sequence containing all of the elements in the input sequence, but ordered in
            a different way. Using a filtering heuristic here will likely result in a progression where many levels use concepts that
            were never introduced.
        obj_heuristic: How the opts of each Objective in the progression should be filtered and ordered. Like level_heuristic, this
            argument should be a function that takes a sequence of Levels and Objectives and returns another sequence of Levels and
            Objectives. The output sequence should contain at least one element from the input sequence, otherwise there will be nothing
            to intoduce the Objective's concept. Also note that some of the levels in an Objective's opts are better at teaching
            the concept than others, so keep that in mind.
        usage_level_heuristic: How the deps of each Level in the progression should be filtered while while computing the usage attribute
            of each. I HIGHlY recommend leaving this as the default takeall- the ordering of the sequence returned by this function does
            not matter, and you'll usually want to use a non-filtering function for level_heuristic anyway.
            Warning: Do not use a usage-filtering heuristic like take_most_used here. As this argument is used to generate the usage
            statistics, the usage statistics will not be fully generated at the time when it is called, which could cause glitches.
        usage_obj_heuristic: How the opts of each Objective in the progression should be filtered while computing the usage statistics.
            If using anything other than the default takeall, I recommend using the same filter in obj_heuristic, optionally composed
            with other heuristics, so that your usage-based heuristics don't have to look at levels whose usage stats were not computed at all.

    Returns:
        A Deque of Level objects ordered as described above. The level parameter will always be the last element, each Level will always
        come somewhere after all the Levels it uses concepts from (as defined by deps and opts), and aside from that, the Levels will be
        selected and ordered based on the various heuristic parameters.
    """
    clearUsages()
    level.calcUsages(usage_level_heuristic, usage_obj_heuristic)
    return level.progression(level_heuristic, obj_heuristic)

def prog_names(levels, note=compose(len, remove_newlines, attrgetter('layout'))):
    """ Formats a progression generated by gen_progression in a human-readable way by putting the name of each level on its
    own line, along with a note that can help inform the user about the decisions that went into generating the progression.

    Args:
        levels: A sequence of Level objects, such as that returned by gen_progression
        note: A function that takes a Level as an argument and returns an object with a .__str__() method, ideally one that relates to
            the gen_progression heuristic parameters. The default computes the size of a Level; attrgetter('usages') will return the level's
            usages stat, etc.

    Returns:
        A single string listing the names of each level in the progression in order, along with whatever the note function returns
        when called on each.
    """
    out = ""
    for elem in levels:
        out += '{} ({})\n'.format(elem.name, note(elem))
    return out

def prog_layouts(levels):
    """ Formats a progression generated by gen_progressions in Puzzlescript-friendly syntax. Each level is numbered sequentially,
    starting at 1. Levels with empty layouts are skipped.

    Args:
        levels: A sequence of Level objects, such as one returned by gen_progressions

    Returns:
        A single string consisting of each level's layout in order, each preceded by a line formatted like 'message Level 1', with
        the 1 replaced by the level's index in the sequence, with enough blank lines thrown in to make it all valid Puzzlescript syntax
    """
    out = ""
    for i, elem in enumerate(filter((lambda a: len(a.layout) > 0), levels), start=1):
        out += 'message Level {}\n\n{}\n\n'.format(i, elem.layout)
    return out

with open('lasers_core.txt') as f:
    game_code = f.read()

def copy_playable(levels):
    """ Combines the Puzzlescript sourcecode read from lasers_core.txt with the layouts of the given levels (as formatted by prog_layouts)
    to create a fully-functional Puzzlescript source file, then copies the whole thing to the system clipboard.

    Args:
        levels: A sequence of Level objects, such as one returned by gen_progressions
    """
    pyperclip.copy(game_code + prog_layouts(levels))

def single_playable(level, postmsg=None, premsg=None):
    """ Generates a playable Puzzlescript source file with a single level, and optional messages to be given to the player before and after the level.

    Args:
        level: A Level object to use in the source file
        postmsg: An optional message to be shown to the player after completing the level
        premsg: An optional message to be shown to the player before seeing the level
            Yes, the postmsg and premsg params appear to be reversed; this is because you're more usually going to want to set postmsg, but not premsg.

    Returns: A single string as described above
    """
    out = [game_code.strip()]
    if premsg is not None:
        out.append('message ' + premsg)
    out.append(level.layout)
    if postmsg is not None:
        out.append('message ' + postmsg)
    return '\n\n'.join(out)

def copy_for_online(levels):
    """ Generates a separate Puzzlescript source file for each level in the given sequence, and copies each in order to the system clipboard.

    When called, this function first prints a prompt including the name of the first level in the progression to stdout. When the user
    presses the Enter key on their keyboard, the function will generate a fully-functional Puzzlescript source file with that level and
    that level alone, but not the level's name, and copy it to the system clipboard. The function will then print a prompt for the next
    level, and so on until it runs out of levels.

    Args:
        levels: A sequence of Level objects, such as one returned by gen_progressions
    """
    for elem in levels:
        input('Press ENTER to copy {}'.format(elem.name))
        pyperclip.copy(single_playable(elem, 'Please exit and return to the survey'))

def gists_for_online(levels):
    """ Generates a series of one-level Puzzlescript source files, uploads each of them as a GitHub gist, and prints out a summary
    with the level names and functional puzzlescript.net/play links.

    See README.txt for details on the setup required to make this function work.
    """
    from PythonGists import PythonGists as PG
    with open('gist.login') as f:
        token = f.read().strip()
    # print(repr(token))
    print('Summary:')
    for l in levels:
        try:
            glink = PG.Gist(l.name, single_playable(l, 'Please exit and return to the survey'), 'script.txt', token)
            gid = glink.split('/')[-1]
            print('{}: https://www.puzzlescript.net/play.html?p={}'.format(l.name, gid))
        except AttributeError:
            pass

first_steps = Level("First Steps", """#########
#.≈..z.$!
#......@#
#......@#
p.µ..t+@#
#########""")
spin_tiles = Objective(first_steps)
have_mirror = Level("Have Mirror, Will Travel", """#########
p.s..g+@#
#......@#
#.œ....@#
#.e....$!
#########""")
crate_expec = Level("Crate Expectations", """#########
#.g+++.$!
#....&+@#
#.*..+.##
p.w.._.##
#########""")
move_tiles = Objective(have_mirror, crate_expec)
button = Objective(crate_expec)
mirror_cube = Level("Weighted Mirror Cube", """####p####
#..ç.f.##
#....&+@#
#+++++.@#
#_.´.a.$!
#########""", button, move_tiles)
half_mirror = Level("Only Half a Mirror", """##g######
p.+....##
#.+....##
h&+.á.a##
#+.+++.##
#+++¥&+$!
####t@###""", spin_tiles, move_tiles)


clear_mud = Level("Clear as Mud", """##@@@@@@@#
#.g.$...›!
#...#.*.##
#.≈.%..a##
p...#...##
##########""", spin_tiles, move_tiles)
mess = Level("A Mess", """#########
#gk.s.k+#
#......+#
#.ß..∑.+#
p..å..å+#
#≈..å..+#
#∑...ß.+#
#∑.....f#
###t$####
####!####""", spin_tiles)
fw1 = Level("FW1", """#########
#.≈..z.›!
#......@#
#......@#
p.µ..t+@#
#########""", spin_tiles)
func_wires = Objective(clear_mud, mess, fw1)

teach_wires = Level("Teaching Wires", """################
#d..ß..##....$.!
#............+##
#......##....+##
#......##....+##
p...t++@@+++++##
################""", spin_tiles, func_wires)
lock_key_1 = Level("Locks and Keys", """####@@@@@@@######
p...@...#.+....$!
#._+$._+$._+++.@#
#...#...@....&+@#
#.*.####@+_+*+.##
#...#...#..&++.##
#._+$.*.#._+...##
#...#...#......##
#################""", button, func_wires)
wall_wires = Objective(teach_wires, lock_key_1)

ft1 = Level("FT1", """####################
p....g+$._++k.._..$!
#....+.#....+..+..@#
#....+.#.*..+..&++@#
#._++i.#....t+++..##
####################""", move_tiles, button, func_wires)
ft2 = Level("FT2", """###################
#..$...›...$...›..!
#.#@###@###@###@###
#..+.g++.g++.g++..#
##.+.+...+...+....#
p.._.+._.+._.+._.*#
##...+.+.+.+.+.+..#
#....i++.i++.i++..#
###################""", move_tiles, button, func_wires, wall_wires)
ft3 = Level("FT3", """###################
#....›...$...›...$!
#.###@###@###@###@#
#....g...g...g...+#
##...+._.+._.+._.+#
p..*.+.+.+.+.+.+._#
##...+.+.+.+.+.+..#
#....i++.i++.i++..#
###################""", move_tiles, button, func_wires, wall_wires)
feed_trip = Objective(ft1, ft2, ft3)

b1 = Level("B1", """########@@@#
p.b.b..g.$!
#..bb.....##
#.........##
#.......bb##
#.bb...b.œ##
#b´.b..b..##
############""", move_tiles)
b2 = Level("B2", """############
p.........$!
#####b####@#
#####.####@#
#...#*#...@#
#.d.%*%.f+@#
#...###...@#
############""", move_tiles)
b3 = Level("B3", """############
p.®..d.ω..$!
#....z....@#
#....e..q.@#
#....#....@#
#.e..b....@#
#####@@@@@@#""", move_tiles, half_mirror)
barrier = Objective(b1, b2, b3)

parity_1 = Level("Parity", """############
p.........$!
#.........@#
#.≈.∑.å.≈.f#
#.........##
#.∑.ß.ß.≈.##
#.........##
#.å...ß.≈.a#
#.........##
#.∑.ß.ß.ß.##
#.........##
############""", spin_tiles)
parity_alt = Level("ParityAlt", """############
p.........$!
#.........@#
#...∑.å.≈.f#
#.........##
#.∑.ß.ß.≈.##
#.........##
#.å...ß.≈.a#
#.........##
#.....ß.ß.##
#.........##
############""", spin_tiles)
mini_parity = Level("MiniParity", """############
p.........$!
#..∑...∑..@#
#.........@#
#d.å.≈.≈.f@#
#.........##
#..ß.∑.ß..##
#.........##
############""", spin_tiles)
parity = Objective(parity_1, parity_alt, mini_parity)

splitmerge_1 = Level("Bad Splittermerge", """##################
p............._.$!
#.............&+@#
#...++h.ø.f++._.##
####@.+...+.@#####
#*.$$.+...+.$$.*##
###@##@###@##@####
#..+..+...+..+..##
#..+..+.k++..+..##
#..+..+......+..##
#..+..+......+..##
#..+.l+.y....+..##
#..+.........+..##
#..+++++t+++++..##
##################""", spin_tiles, move_tiles, button, half_mirror, wall_wires)
splitmerge_2 = Level("Flashing Splittermerge", """#################
p..++++........$!
#..+#.&++++++++@#
#..+¨.+.ω...¥..##
#..+t.+...ç....##
#..+..+.t......##
###@##@#@##%#%###
#.d›..+.+.z.....#
#.....g.+.......#
#...g...+.......#
#...&+$.+..bk›..#
#...b...+.......#
#.....i.+.t›ti..#
#...i++++..w....#
#################""", spin_tiles, move_tiles, half_mirror, wall_wires)
splitmerge_3 = Level("Next Splittermerge", """##############
#..._@+++...##
p.*.k.¥.+...$!
#..#....+...@#
#_l...f.+...@#
#@....+.+...@#
#+..t&+.+...@#
#+...+..+...@#
#+&+++&++...@#
#.+...+.....@#
##$###$##...@#
#...#...#...@#
#...#.¨.%.f.@#
#...#...#.&+@#
#.¨.%...%.f.##
#...#...#...##
##############""", spin_tiles, move_tiles, half_mirror, wall_wires)
splitmerge_4 = Level("Fourth Splittermerge", """##################
#######.......####
p...$.$.c.≥.z.$.$!
#..#@#@+b...b+@#@#
#..#@###%###%###@#
#...++g++++++++++#
#................#
#.....e.œ...®....#
##################""", spin_tiles, move_tiles, half_mirror, wall_wires)
splittermerge = Objective(splitmerge_1, splitmerge_2, splitmerge_3, splitmerge_4)

beamlock_1 = Level("Beamlock", """##@@@#######
p.k.g.s..¥$!
#.........@#
#...e...z.@#
#.........@#
#.......q.@#
#.....´...@#
#...t.....@#
####@@@@@@@#""", move_tiles, splittermerge, func_wires, wall_wires)
beamlock_2 = Level("Beamlock 2", """########
p..s..$!
#....´@@
#..ω.f#@
#....+#@
#l...&@@
#+...+##
#++t++##
########""", move_tiles, func_wires)
beamlock = Objective(beamlock_1, beamlock_2)

hodor_1 = Level("Hodor", """##########
p.......$!
#.*...*.@#
#.......@#
#...####@#
#...#...@#
#.._$._+@#
#...#...##
##########""", move_tiles, func_wires)
hodor_2 = Level("Hodor 2", """########
p.....##
#.....##
#.*.*.$!
#.....@#
#.....@#
###›##@#
#..+..@#
#..+..@#
#.._++@#
#.....##
#.....##
########""", move_tiles, func_wires)
hodor = Objective(hodor_1, hodor_2)

experiment = Level("Experiment", """#@@@@@@@@###
#@.....%+.ô#
#@.....%+..#
#@..h..%_z.#
#@..+..%...#
#@..+..%...#
#@..+..%...#
#@##@##c.≈##
#@..+......#
#@..+......#
!›$+&......#
##..+......#
##..h..ø...#
##.........#
######p#####""", spin_tiles, move_tiles, func_wires, wall_wires)
slight_compact = Level("Slightly Compacted", """...##@@@@@@++++++.
...#.+...##.....+.
...#.+.g+@#.....+.
...#+&+..@#.....+.
...#g.g..@#.....+.
####.c..z@@@@@@#@#
#.c....qe.b.z.@#@#
#.....ezc....f@#@#
p....e..ø.q...›.$!
#.e.ø.......ø.z###
#......e......q###
##################""", spin_tiles, func_wires, wall_wires)
bad_sensor = Objective(experiment, slight_compact)

wirefu = Level("WireFu", """####@@@@@##########
p...g...@.........#
#.......$++_._+++k#
#.......#.........#
@h..¨..f@..g+.....#
@.......@...+.....#
@.......@l.å+&+++t#
@...t...#....+...+#
@@$#@@@@@#$@@@._.+#
@.+.....@...###›#@#
@.++++g.@.µ.#....+#
@.......@...#....+#
@@›##...@%%%#..*.+#
#...#...@...#....+#
#.*.#.ø.$.t+$....+#
#...#...#...###$@@#
###############!###""", func_wires, wall_wires, spin_tiles, move_tiles)

all_objs = Level("All Objectives Complete", "", func_wires, wall_wires, feed_trip, barrier, parity, splittermerge, beamlock, hodor, bad_sensor, secret=True)

print(prog_names(gen_progression(all_objs, usage_obj_heuristic=takefirst)))
# print(prog_names(gen_progression(all_objs, smaller_first, takeall)))
# print(prog_names(gen_progression(all_objs, larger_first, takeall)))

print(prog_names(gen_progression(all_objs, frontload, takeall), note=attrgetter('usages')))
print(prog_names(gen_progression(all_objs, backload, takeall), note=attrgetter('usages')))

# copy_for_online(gen_progression(all_objs, usage_obj_heuristic=takefirst))

# gists_for_online([first_steps, mess, wirefu])
# gists_for_online(allLevels)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


