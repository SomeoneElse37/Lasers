
from collections import deque
from operator import itemgetter, attrgetter
import pyperclip

def compose(*funcs):
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
    l = []
    for level in levels:
        l.extend(level.progression(takenone, kw['obj_heuristic']))
    return sorted(l, key=compose(len, remove_newlines, attrgetter('layout')))

def larger_first(levels, **kw):
    l = []
    for level in levels:
        l.extend(level.progression(takenone, kw['obj_heuristic']))
    return sorted(l, key=compose(len, remove_newlines, attrgetter('layout')), reverse=True)

allLevels = []

def clearUsages():
    for elem in allLevels:
        elem.usages = 0

class Level:
    def __init__(self, name, layout, *deps):
        self.name = name
        self.layout = layout
        self.deps = deps
        self.usages = 0
        allLevels.append(self)

    def progression(self, level_heuristic=takeall, obj_heuristic=takefirst):
        prog = deque()
        prog.append(self)
        for dep in reversed(level_heuristic(self.deps, obj_heuristic=obj_heuristic)):
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
    def __init__(self, *opts):
        self.opts = opts
        self.usages = 0
        allLevels.append(self)

    def progression(self, level_heuristic=takeall, obj_heuristic=takefirst):
        prog = deque()
        for elem in obj_heuristic(self.opts, obj_heuristic=obj_heuristic):
            prog.extend(elem.progression(level_heuristic, obj_heuristic))
        return prog

    def calcUsages(self, level_heuristic=takeall, obj_heuristic=takefirst):
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
    clearUsages()
    level.calcUsages(usage_level_heuristic, usage_obj_heuristic)
    return level.progression(level_heuristic, obj_heuristic)

def prog_names(levels):
    out = ""
    for elem in levels:
        out += elem.name + ' (' + str(len(elem.layout.replace('\n', ''))) + ')\n'
    return out

def prog_layouts(levels):
    out = ""
    for i, elem in enumerate(filter((lambda a: len(a.layout) > 0), levels), start=1):
        out += 'message Level {}\n\n{}\n\n'.format(i, elem.layout)
    return out

with open('lasers_core.txt') as f:
    game_code = f.read()

def copy_playable(levels):
    pyperclip.copy(game_code + prog_layouts(levels))

def copy_for_online(levels):
    for elem in levels:
        input('Press ENTER to copy {}'.format(elem.name))
        pyperclip.copy(game_code + elem.layout)


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

all_objs = Level("All Objectives Complete", "", func_wires, wall_wires, feed_trip, barrier, parity, splittermerge, beamlock, hodor, bad_sensor)

print(prog_names(gen_progression(all_objs, usage_obj_heuristic=takefirst)))
print(prog_names(gen_progression(all_objs, smaller_first, takeall)))
print(prog_names(gen_progression(all_objs, larger_first, takeall)))

# copy_for_online(gen_progression(all_objs, usage_obj_heuristic=takefirst))






