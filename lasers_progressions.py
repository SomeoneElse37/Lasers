"""
A script to generate level progressions for the Lasers game.

The layouts of and dependency relations between a selection of levels are hardcoded into this script.
At the moment, the script basically just provides a collection of tools for ordering the levels in a progression,
but in the future I hope to grant access to those tools from the command line.
"""

from collections import deque
from operator import itemgetter, attrgetter, methodcaller
from itertools import zip_longest
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

def formattify(template, *nfuncs, **kwfuncs):
    """ A very flexible tool for creating functions that convert an object into a formatted string.

    >>> add1 = lambda n: n + 1
    >>> times2 = lambda n: n * 2
    >>> add3 = lambda n: n + 3
    >>> ident = lambda n: n
    >>> f = formattify('{n} + 1 = {}; {n} * 2 = {}; {n} + 3 = {}', add1, times2, add3, n=ident)
    >>> f(4)
    '4 + 1 = 5; 4 * 2 = 8; 4 + 3 = 7'

    Args:
        template: An object with a .format() method; typically a string
        *nfuncs: An arbitrary number of functions that take a single object and return whatever template.format() will accept
        **kwfuncs: An arbitrary number of functions bound to keywords that take a single object and, once again, return
            objects of whatever types template.format() will look for

    Returns: A function that takes a single object as an argument, passes it to each function in *nfuncs and **kwfuncs,
        and passes all the results to template.format().
    """
    def inner(p):
        nargs = [f(p) for f in nfuncs]
        kwargs = {k:f(p) for (k, f) in kwfuncs.items()}
        return template.format(*nargs, **kwargs)
    return inner

def remove_newlines(s):
    """ Strips all the newline characters (\\n) from the given input string.

    >>> remove_newlines('abcd\\nefgh')
    'abcdefgh'

    Args:
        s: The sreing to remove newlines from.

    Returns: A new string with all the \\n characters deleted.
    """
    return s.replace('\n', '')

###############################################################################################################################################
# Heuristic Section                                                                                                                           #
#                                                                                                                                             #
# The following functions are all what the rest of this file calls "heuristics".                                                              #
#                                                                                                                                             #
# Each takes as input a slicable sequence (e.g. list or tuple- no deques here) of Level objects and an arbitrary set of keyword arguments.    #
# At the moment, all the keyword arguments are completely ignored, although that may change in the future.                                    #
#                                                                                                                                             #
# Each returns another sequence of Level objects, usually either the same type as the input or just a list.                                   #
# The Levels in this output sequence are always a subset of the input Levels.                                                                 #
#                                                                                                                                             #
# These functions are passed to gen_prorgessions and related functions to determine which Levels should appear in the final progression       #
# and to help determine how those Levels should be ordered. gen_progressions imposes a partial ordering upon the progressions it generates    #
# based on the levels' dependency relations, but that still leaves quite a lot of leeway. These heuristics help fill that gap by being called #
# on various sub-progressions. If one of these heuristics returns a sequence that breaks the dependency relations, gen_progressions will      #
# fix it by making minimal changes to the sequence returned by the heuristic.                                                                 #
#                                                                                                                                             #
# These heuristics can be combined by using the compose() function defined above. For example, to return only the largest level from the      #
# input list, you can use this: compose(takefirst, larger_first)                                                                              #
# This combined heuristic (that is, the function returned by compose()) will satisfy all the type requirements mentioned above, and can in    #
# theory be passed to gen_progressions with no issues.                                                                                        #
###############################################################################################################################################

def takeall(levels, **_):
    """ Essentially a no-op. Takes a sequence of Level objects and returns it unchanged.

    >>> takeall([1, 2, 3, 4])
    [1, 2, 3, 4]

    Args:
        levels: A sequence of Level objects

    Returns: The exact same sequence of Level objects
    """
    return levels

def takeall_reversed(levels, **_):
    """ Reverses a sequence of Level objects.

    >>> takeall_reversed([1, 2, 3, 4])
    [4, 3, 2, 1]

    Args:
        levels: A sequence of Level objects

    Returns: A list containing the same Level objects, in reverse order.
    """
    return list(reversed(levels))

def takefirst(levels, **_):
    """ Returns the first element in the given Level sequence, returning it as a singleton sequence.

    >>> takefirst([1, 2, 3, 4])
    [1]

    Args:
        levels: A slicable sequence of Level objects (deques won't work here, but lists and tuples will)

    Returns: A singleton sequence of the same type as the input (usually?) containing the first element form the input sequence
    """
    return levels[0:1]

def frontload_base(levels, **_):
    """ Sorts Levels based on their own usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) first.

    Technically works by sorting by the Levels' own usages attributes, not by any computation performed on those attributes.
    I'm not certain that this works any differently when used to generate a progression than any other frontload heuristic.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in frontload_base(T1_all)]
    ['2L4', '1L5', '1L6', '1L3', '0L7']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come first.
    """
    return sorted(levels, key=attrgetter('usages'), reverse=True)

def backload_base(levels, **_):
    """ Sorts Levels based on their usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) as close to the levels where those concepts are actually used as possible.

    Technically works by sorting by the Levels' own usages attributes, not by any computation performed on those attributes.
    This can lead to situations where progressions generated using this heuristic have more-used levels coming before less-used
    levels when there's no real reason for it, due to a quirk in how .progression() works, when really I'd like the more-used
    levels to come as late as possible. So this is less than ideal.

    Each dependency of the root level has a usage of exactly 1 (assuming that none of them depend on each other), so this heuristic
    cannot distinguish between them. As .progression() calls its heuristic on each of those dependencies, that's the source
    of the error.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in backload_base(T1_all)]
    ['0L7', '1L5', '1L6', '1L3', '2L4']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come last.
    """
    return sorted(levels, key=attrgetter('usages'))

def frontload_max(levels, **_):
    """ Sorts Levels based on their dependencies' usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) first.

    Technically works by sorting by the maximum usages attribute of any of the Level's dependencies, their dependencies, etc.
    I'm not certain that this works any differently when used to generate a progression than any other frontload heuristic.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in frontload_max(T1_all)]
    ['2L4', '1L6', '1L3', '0L7', '1L5']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come first.
    """
    return sorted(levels, key=methodcaller('max_leaf_usage'), reverse=True)

def backload_max(levels, **_):
    """ Sorts Levels based on their usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) as close to the levels where those concepts are actually used as possible.

    Technically works by sorting by the maximum usages attribute of any of the Level's dependencies, their dependencies, etc.
    As such, this heuristic cannot distinguish between different levels that depend on the most-used leaf level- which, by
    definition, has a lot of levels that depend on it. So that's less than ideal.

    This heuristic was created in an attempt to solve the problems with backload_base, with partial success.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in backload_max(T1_all)]
    ['1L5', '2L4', '1L6', '1L3', '0L7']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come last.
    """
    return sorted(levels, key=methodcaller('max_leaf_usage'))

def frontload_sum(levels, **_):
    """ Sorts Levels based on their usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) first.

    Technically works by sorting by the Level's .sum_leaf_usage() methods, which compute the sum of the usages of the Level's
    dependencies that have no deps of their own, counting each as many times as it appears as a dependency.
    I'm not certain that this works any differently when used to generate a progression than any other frontload heuristic.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in frontload_sum(T1_all)]
    ['0L7', '2L4', '1L6', '1L3', '1L5']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come first.
    """
    return sorted(levels, key=methodcaller('sum_leaf_usage'), reverse=True)

def backload_sum(levels, **_):
    """ Sorts Levels based on their usage data, so that gen_progression() will put the most-used levels (representing those
    that introduce the most basic concepts) as close to the levels where those concepts are actually used as possible.

    Technically works by sorting by the Level's .sum_leaf_usage() methods, which compute the sum of the usages of the Level's
    dependencies that have no deps of their own, counting each as many times as it appears as a dependency.

    This heuristic was created in an attempt to provide something between backload_base and backload_max, as they each did
    parts of what I really wanted to do.

    Precondition: All elements of levels have already had their usage information computed, e.g. by calling .calcUsages() on
        the root Level of the progression (which gen_progression() does)

    >>> clearUsages()
    >>> T1_0L7.calcUsages()
    >>> [l.name for l in backload_sum(T1_all)]
    ['1L5', '2L4', '1L6', '1L3', '0L7']

    Args:
        levels: A sequence of Level objects.

    Returns: A list (specifically a list, not a tuple or deque or whatever) containing all the same Level objects, sorted
        so that the most-used Levels come last.
    """
    return sorted(levels, key=methodcaller('sum_leaf_usage'))

def takenone(levels, **_):
    """ Completely ignores the input sequence and returns an empty tuple.

    Potentially useful if you want to generate a progression that completely ignores Objectives... or something like that.
    I don't even remember why I wrote this function.

    >>> takenone([1, 2, 3, 4])
    ()

    Args:
        levels: A sequence of Level objects. COmpletely ignored.

    Returns: The empty tuple ()
    """
    return ()

def smaller_first(levels, **_):
    """ Sorts the input levels by their size- that is, by the actual number of grid squares present when loaded into PuzzleScript.

    >>> [l.name for l in smaller_first(T1_all)]
    ['1L3', '2L4', '1L5', '1L6', '0L7']

    Args:
        levels: A sequence of Level objects

    Returns: A list containing the same Levels, sorted such that the samller levels appear first.
    """
    return sorted(levels, key=compose(len, remove_newlines, attrgetter('layout')))

def larger_first(levels, **_):
    """ Sorts the input levels by their size- that is, by the actual number of grid squares present when loaded into PuzzleScript- and reverses the result.

    >>> [l.name for l in larger_first(T1_all)]
    ['0L7', '1L6', '1L5', '2L4', '1L3']

    Args:
        levels: A sequence of Level objects

    Returns: A list containing the same Levels, sorted such that the larger levels appear first.
    """
    return sorted(levels, key=compose(len, remove_newlines, attrgetter('layout')), reverse=True)

def by_lnum(levels, **_):
    """ Sorts the input levels by their internal lnum value, guaranteeing a total ordering. Handy for debugging.

    Use this as the rightmost heuristic in a compose()'d chain, and compare it with a compose()'d
    chain with reversed_lnum() as the rightmost heuristic to see to what extent the other heuristics
    in the chain and the gen_progression dependency partial ordering actually determine the result.

    Args:
        levels: A sequence of Level objects

    Returns: A list containing the same Level objects, sorted in an arbitrary (but reliable) order.
    """
    return sorted(levels, key=attrgetter('lnum'))

def reversed_lnum(levels, **_):
    """ Sorts the input levels by their internal lnum value in reverse order, guaranteeing a total ordering. Handy for debugging.

    This is just like by_lnum, but sorts in reverse order. See by_lnum for more details.

    Args:
        levels: A sequence of Level objects

    Returns: A list containing the same Level objects, sorted in an arbitrary (but reliable) order.
    """
    return sorted(levels, key=attrgetter('lnum'), reverse=True)

def preference(levels, **_):
    """ Rearranges the input levels so that the ones with the 'preferred' tag set to True come first.

    I recommend combining this with takefirst: compose(takefirst, preference, some_other_heuristic)

    Args:
        levels: A sequence of Level objects

    Returns: The same sequence, but with all the preferred levels at the front
    """
    return sorted(levels, key=attrgetter('preferred'), reverse=True)

#####################################################################################################################
# End of heuristic section. Beyond this point lies normal Python code that doesn't adhere to the description above. #
#####################################################################################################################

# global_lnum = 1

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
        lnum: A unique ID for the Level, based on the order in which the Level objects are created. Useful for debugging.
            Messing with this could cause problems. Functions that use it are not thread-safe.
        preferred: A tag applied to levels that the developers subjectively like and think are better than the alternatives which may show up in some progressions. Doesn't do anything on its own, but can be read by heuristics.
    """
    def __init__(self, name, layout, *deps, preferred=False):
        """ Initializes a new Level object.

        Args:
            name: A string, representing the name of the level. This won't usually be shown to players.
            layout: The layout of the level, in Puzzlescript's ASCII-art-like syntax. See the link in README.md for examples of how Lasers interprets
                this syntax, and click the "Level Editor" link at the top for assistance in creating syntactically-valid levels.
            *deps: A variable number of Level and Objective objects, each representing a concept that this Level uses.
            preferred: Whether or not to mark this Level's preferred flag.
        """
        self.name = name
        self.layout = layout
        self.deps = deps
        self.usages = 0
        allLevels.append(self)
        self.lnum = len(allLevels)
        self.preferred = preferred

    def flatten(self, *_, **__):
        """ Returns this Level wrapped up as a singleton list.

        Really only interesting because Objective.flatten() does something entirely different,
        and the best way to implement it was for Levels to have a flatten() method that just
        returns themselves in a singleton list.

        Takes an arbitrary set of positional and keyword arguments and ignores them all. Again,
        this is just for compatibility with the much more interesting Objective.flatten().

        Returns: Itself in a singleton list. As I'm sure you could guess at this point.
        """
        return [self]

    def flat_deps(self, obj_heuristic=takefirst):
        """ 'Flattens' this Level's deps, converting each Objective therein into a sequence of Levels.

        Builds up a list by calling .flatten() on each of this object's deps and concatenating the results
        together. There is a possibility for duplicate entries in the resulting list, if self.deps includes
        Objectives with overlapping opts or a Level and an Objective with that Level as one of its opts.

        Args:
            obj_heuristic: How the opts of each Objective encountered should be filtered and sorted. See
                the documentation for gen_progression(), Level.progression() and Objective.progression() for more details.
                Note that any sorting done here will usually be overridden, as Level.progression() calls
                level_heuristic on the list returned by this function.

        Returns: A list of Level objects drawn from this Level's deps, with each Objective therein replaced by
            a sequence of Levels drawn from its opts
        """
        l = []
        for dep in self.deps:
            l.extend(dep.flatten(obj_heuristic))
        return l

    def max_leaf_usage(self):
        """ Fetches the maximum usage of this level's deps, their deps/opts, etc.

        This is what the frontload and backload heuristics *actually* look at.

        >>> clearUsages()
        >>> T1_0L7.calcUsages()
        >>> T1_0L7.usages
        0
        >>> T1_2L4.usages
        2
        >>> T1_0L7.max_leaf_usage()
        2

        Returns: An integer, equal to the highest usage stat found in this Level or anything it depends on.
        """
        return max([l.max_leaf_usage() for l in self.deps], default=self.usages)

    def sum_leaf_usage(self):
        """ Computes the sum of the usage stats of each 'leaf' node in this Level's dependencies.

        If this Level has no deps, return self.usages. This is what I mean by a 'leaf' node.
        If this Level has deps, recursively call this method on each of them and add the results. Do not include
            this Level's usages in the result, as it already counts toward each of the deps' usages.

        >>> clearUsages()
        >>> T1_0L7.calcUsages()
        >>> T1_1L5.sum_leaf_usage()
        1
        >>> T1_2L4.sum_leaf_usage()
        2
        >>> T1_1L3.sum_leaf_usage()
        2
        >>> T1_0L7.sum_leaf_usage()
        5

        Returns: An integer, as described above.
        """
        if len(self.deps) == 0:
            return self.usages
        else:
            return sum([l.sum_leaf_usage() for l in self.deps])

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
        for elem in level_heuristic(self.flat_deps(obj_heuristic)):
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
            *opts: A variable number of Level and Objective objects that could each be used to introduce the concept that this Objective represents.
        """
        self.opts = opts
        self.usages = 0
        allLevels.append(self)

    def flatten(self, obj_heuristic=takefirst):
        """ Generates a list of Levels based on this Objective's opts.

        This method recursively calls .flatten() on each element in self.opts, then concatenates the resulting lists together.
        As Level.flatten() simply returns the Level itself (wrapped in a singleton list), the result will always be a list of Level objects.

        After the recursion-concatenation flattening process is complete, obj_heuristic is called on the result. While it is true that each
        Level in self.opts will only appear once in the concatenated list, while any Objectives in self.opts may have several representatives,
        this *should* not cause any problems. If obj_heuristic only returns one element from the list it's given, then each Objective in
        self.opts will have only one representative, so that's fair. If obj_heuristic doesn't do any filtering, then Objectives in self.opts
        may well return multiple representatives, but in that case returning all of them is the whole point. If obj_heuristic only returns, say,
        two elements from its input list, then those two elements may well be from the same nested Objective- but if you're nesting Objectives,
        then that implies that any of the inner Objective's opts would fulfill this Objective's concept as well as any anything else in self.opts,
        so no problem there.

        If you can think of a scenario where this behavior is demonstrably wrong, please let me know.

        Args:
            obj_heuristic: How the Levels returned by the recursion-concatenation process should be filtered and sorted before being returned.
                Note that any sorting done here will usually be overridden by a level_heuristic call later on in the function that called this
                method. Level.progression() certainly will do that.

        Returns: A list of Level objects created from this Objective's opts, as described above.
        """
        l = []
        for opt in self.opts:
            l.extend(opt.flatten(obj_heuristic))
        return obj_heuristic(l)

    def max_leaf_usage(self):
        """ Fetches the maximum usage of this objective's opts, their opts/deps, etc.

        This is what the frontload and backload heuristics *actually* look at.

        # >>> clearUsages()
        # >>> T1_0L7.calcUsages()
        # >>> T1_0L7.usages
        # 0
        # >>> T1_2L4.usages
        # 2
        # >>> T1_0L7.max_leaf_usage
        # 2

        Returns: An integer, equal to the highest usage stat found in any of this Objective's opts
            or any of their depenencies.
        """
        return max([l.max_leaf_usage() for l in self.opts], default=self.usages)

    def sum_leaf_usage(self):
        """ Computes the sum of the usage stats of each 'leaf' node in this Objective's opts.

        If this Objective has no opts, return self.usages (which will normally be 0).
        If this Objective has opts, recursively call this method on each of them and add the results.

        Returns: An integer, as described above.
        """
        if len(self.opts) == 0:
            return self.usages
        else:
            return sum([l.sum_leaf_usage() for l in self.opts])

    def progression(self, level_heuristic=takeall, obj_heuristic=takefirst):
        """ Generates a progression for each of this Objective's opts, and strings them all together.

        Unlike Level.progression() and gen_progression() (which calls Level.progression()), this method DOES NOT ensure that the returned deque
        does not contain any duplicate levels. It simply calls .progression() on each object returned by obj_heuristic(self.opts), and concatenates
        them all together. If obj_heuristic is the default takefirst or otherwise only returns one object from its argument, then this method will
        simply return that selected object's progression, which will in that case not have any duplicate entries; but if obj_heuristic can return
        multiple elements, this method can and usually will return duplicates.

        Warning: This method is now deprecated. Its functionality is now baked into Level.progression() and Objective.flatten().

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

        Warning: This method is now deprecated. Its functionality is now baked into Level.calcUsages() and Objective.flatten().

        Args:
            level_heuristic: How the deps of the Levels in the progression should be filtered.
                There's really not a good reason to use anything other than the default takeall, as far as I know.
            obj_heuristic: How the opts of this and other Objectives in the progression should be filtered. Should be a superset of
                the objects returned by the obj_heuristic parameter of a subsequent call to self.progression().
        """
        print('Warning: Objective.calcUsages() is now deprecated')
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

    >>> [l.name for l in gen_progression(T1_0L7)]
    ['2L4', '1L3', '1L6', '1L5', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, frontload_base)]
    ['2L4', '1L3', '1L6', '1L5', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, backload_base)]
    ['2L4', '1L3', '1L6', '1L5', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, frontload_max)]
    ['2L4', '1L3', '1L6', '1L5', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, backload_max)]
    ['1L5', '2L4', '1L3', '1L6', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, frontload_sum)]
    ['2L4', '1L3', '1L6', '1L5', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, backload_sum)]
    ['1L5', '2L4', '1L3', '1L6', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, smaller_first)]
    ['2L4', '1L3', '1L5', '1L6', '0L7']
    >>> [l.name for l in gen_progression(T1_0L7, larger_first)]
    ['2L4', '1L6', '1L5', '1L3', '0L7']

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

default_note = formattify('Size ={:4}, Usages ={:3}, Max ={:4}, Sum ={:5}', compose(len, remove_newlines, attrgetter('layout')), \
        attrgetter('usages'), methodcaller('max_leaf_usage'), methodcaller('sum_leaf_usage'))

def lvl_name(level, note=default_note):
    """ Prettyprints the name of the given Level along with an optional message.

    Args:
        level: The Level to be printed
        note: A Level -> String function, as described in prog_names
    """
    if level is None:
        return ''
    else:
        return '{:25} ({})'.format(level.name, note(level))

def prog_names(levels, note=default_note):
    """ Formats a progression generated by gen_progression in a human-readable way by putting the name of each level on its
    own line, along with a note that can help inform the user about the decisions that went into generating the progression.

    Args:
        levels: A sequence of Level objects, such as that returned by gen_progression
        note: A function that takes a Level as an argument and returns an object with a .__str__() method, ideally one that relates to
            the gen_progression heuristic parameters. The default includes the size of the Level and the numbers used by the three
            different frontload/backload heuristics.

    Returns:
        A single string listing the names of each level in the progression in order, along with whatever the note function returns
        when called on each.
    """
    out = ""
    for elem in levels:
        out += lvl_name(elem, note) + '\n'
    return out

def debug_progressions(level, level_heuristic=takeall, obj_heuristic=takefirst, usage_level_heuristic=takeall, usage_obj_heuristic=takeall):
    """ Generates two progressions based on the inputs, and prints them side-by-side for debug purposes.

    Each progression has all ties broken by lnum. The left-hand preogression sorts by lnum normally, while
    the right-hand progression sorts by lnum in reverse order.

    Args: Exactly the same as gen_progression. Go read that function's documentation.

    Returns: A single string, comparing the two progressions side by side.
    """
    prog1 = gen_progression(level, compose(level_heuristic, by_lnum), compose(obj_heuristic, by_lnum),
            compose(usage_level_heuristic, by_lnum), compose(usage_obj_heuristic, by_lnum))
    names1 = [lvl_name(a) for a in prog1]
    prog2 = gen_progression(level, compose(level_heuristic, reversed_lnum), compose(obj_heuristic, reversed_lnum),
            compose(usage_level_heuristic, reversed_lnum), compose(usage_obj_heuristic, reversed_lnum))
    names2 = [lvl_name(b) for b in prog2]
    out = []
    for a, b in zip_longest(names1, names2):
        out.append('{}   #   {}\n'.format(a, b))
    return ''.join(out)

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
glass = Objective(clear_mud)

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

multi_wires = Objective(lock_key_1)

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
###################""", move_tiles, button, func_wires, wall_wires, preferred=True)
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
############""", move_tiles, glass)
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
#################""", spin_tiles, move_tiles, half_mirror, wall_wires, glass)
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
##############""", spin_tiles, move_tiles, half_mirror, wall_wires, glass)
splitmerge_4 = Level("Fourth Splittermerge", """##################
#######.......####
p...$.$.c.≥.z.$.$!
#..#@#@+b...b+@#@#
#..#@###%###%###@#
#...++g++++++++++#
#................#
#.....e.œ...®....#
##################""", spin_tiles, move_tiles, half_mirror, wall_wires, glass, preferred=True)
splittermerge = Objective(splitmerge_1, splitmerge_2, splitmerge_3, splitmerge_4)

beamlock_1 = Level("Beamlock", """##@@@#######
p.k.g.s..¥$!
#.........@#
#...e...z.@#
#.........@#
#.......q.@#
#.....´...@#
#...t.....@#
####@@@@@@@#""", move_tiles, splittermerge, func_wires, wall_wires, preferred=True)
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
######p#####""", spin_tiles, move_tiles, func_wires, wall_wires, glass)
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
###############!###""", func_wires, wall_wires, spin_tiles, move_tiles, multi_wires, button, glass)

talos = Level('Talos', """########################
p..ç´¥¥...$.....#.....##
#.........@.....#.....##
#......r.f@.....#.....##
#...#.....@.....#.....##
#...#c.%..$..a..#.._..##
#...#.....#.....#..+..##
#...#.....#.....$..&++$!
#...#.....#.....@..+..##
#...#.....%....f@.._..##
#...#t....#.....#.....##
#...#@@$###.....#.....##
#........a#.....#.....##
#.........#.....#.....##
########################""", move_tiles, button, mirror_cube, half_mirror, func_wires, feed_trip, splittermerge, beamlock, glass)

all_objs = Level("All Objectives Complete", "", func_wires, wall_wires, multi_wires, feed_trip, barrier, parity, splittermerge, beamlock, hodor, bad_sensor, wirefu)

wire_talos = Level("WireFu+Talos Complete", "", wirefu, talos)

print(debug_progressions(all_objs, usage_obj_heuristic=takefirst))
# print(prog_names(gen_progression(all_objs, smaller_first, takeall)))
# print(prog_names(gen_progression(all_objs, larger_first, takeall)))

print(' ========== frontload_base ========== ')
print(debug_progressions(all_objs, frontload_base, takeall))
print(' ========== frontload_max ========== ')
print(debug_progressions(all_objs, frontload_max, takeall))
print(' ========== frontload_sum ========== ')
print(debug_progressions(all_objs, frontload_sum, takeall))

print(' ========== backload_base ========== ')
print(debug_progressions(all_objs, backload_base, takeall))
print(' ========== backload_max ========== ')
print(debug_progressions(all_objs, backload_max, takeall))
print(' ========== backload_sum ========== ')
print(debug_progressions(all_objs, backload_sum, takeall))

print(' ========== WireFu ========== ')
print(debug_progressions(wirefu, by_lnum, takeall))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, frontload_base)))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, backload_base)))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, frontload_max)))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, backload_max)))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, frontload_sum)))
print(debug_progressions(wirefu, by_lnum, compose(takefirst, backload_sum)))

print(' ========== Trying to get compact all_objs progressions ========== ')
print(debug_progressions(all_objs, by_lnum, compose(takefirst, frontload_base)))
print(debug_progressions(all_objs, by_lnum, compose(takefirst, backload_base)))

print(' ========== WireFu + Talos ========== ')
print(debug_progressions(wire_talos, frontload_sum, compose(takefirst, preference, frontload_base)))
print(debug_progressions(wire_talos, backload_sum, compose(takefirst, preference, frontload_base)))

# input('Press ENTER to copy the frontloaded progression')
# copy_playable(gen_progression(wire_talos, frontload_sum, compose(takefirst, preference, frontload_base)))
# input('Press ENTER to copy the backloaded progression')
# copy_playable(gen_progression(wire_talos, backload_sum, compose(takefirst, preference, frontload_base)))

# copy_for_online(gen_progression(all_objs, usage_obj_heuristic=takefirst))

# gists_for_online([first_steps, mess, wirefu])
# gists_for_online(allLevels)

# For Testing
# Tree 1 (all nodes are Levels and depend on linked nodes below them)
# Node syntax: uLs, where u = expected usages and s = size
#     0L7
#    / | \
# 1L3 1L6 |
#   \ /   |
#   2L4  1L5
T1_1L5 = Level('1L5', '#####')
T1_2L4 = Level('2L4', '####')
T1_1L6 = Level('1L6', '######', T1_2L4)
T1_1L3 = Level('1L3', '###', T1_2L4)
T1_0L7 = Level('0L7', '#######', T1_1L3, T1_1L6, T1_1L5)
T1_all = [T1_1L5, T1_2L4, T1_1L6, T1_1L3, T1_0L7]

if __name__ == "__main__":
    import doctest
    doctest.testmod()


