#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/randomtext.py

__version__='3.3.0'

###############################################################################
#   generates so-called 'Greek Text' for use in filling documents.
###############################################################################
__doc__="""Like Lorem Ipsum, but more fun and extensible.

This module exposes a function randomText() which generates paragraphs.
These can be used when testing out document templates and stylesheets.
A number of 'themes' are provided - please contribute more!
We need some real Greek text too.

There are currently six themes provided:
    STARTUP (words suitable for a business plan - or not as the case may be),
    COMPUTERS (names of programming languages and operating systems etc),
    BLAH (variations on the word 'blah'),
    BUZZWORD (buzzword bingo),
    STARTREK (Star Trek),
    PRINTING (print-related terms)
    PYTHON (snippets and quotes from Monty Python)
    CHOMSKY (random lingusitic nonsense)

EXAMPLE USAGE:
    from reportlab.lib import randomtext
    print randomtext.randomText(randomtext.PYTHON, 10)

    This prints a random number of random sentences (up to a limit
    of ten) using the theme 'PYTHON'.

"""

#theme one :-)
STARTUP = ['strategic', 'direction', 'proactive', 'venture capital',
    'reengineering', 'forecast', 'resources', 'SWOT analysis',
    'forward-thinking', 'profit', 'growth', 'doubletalk', 'B2B', 'B2C',
    'venture capital', 'IPO', "NASDAQ meltdown - we're all doomed!"]

#theme two - computery things.
COMPUTERS = ['Python', 'Perl', 'Pascal', 'Java', 'Javascript',
    'VB', 'Basic', 'LISP', 'Fortran', 'ADA', 'APL', 'C', 'C++',
    'assembler', 'Larry Wall', 'Guido van Rossum', 'XML', 'HTML',
    'cgi', 'cgi-bin', 'Amiga', 'Macintosh', 'Dell', 'Microsoft',
    'firewall', 'server', 'Linux', 'Unix', 'MacOS', 'BeOS', 'AS/400',
    'sendmail', 'TCP/IP', 'SMTP', 'RFC822-compliant', 'dynamic',
    'Internet', 'A/UX', 'Amiga OS', 'BIOS', 'boot managers', 'CP/M',
    'DOS', 'file system', 'FreeBSD', 'Freeware', 'GEOS', 'GNU',
    'Hurd', 'Linux', 'Mach', 'Macintosh OS', 'mailing lists', 'Minix',
    'Multics', 'NetWare', 'NextStep', 'OS/2', 'Plan 9', 'Realtime',
    'UNIX', 'VMS', 'Windows', 'X Windows', 'Xinu', 'security', 'Intel',
    'encryption', 'PGP' , 'software', 'ActiveX', 'AppleScript', 'awk',
    'BETA', 'COBOL', 'Delphi', 'Dylan', 'Eiffel', 'extreme programming',
    'Forth', 'Fortran', 'functional languages', 'Guile', 'format your hard drive',
    'Icon', 'IDL', 'Infer', 'Intercal', 'J', 'Java', 'JavaScript', 'CD-ROM',
    'JCL', 'Lisp', '"literate programming"', 'Logo', 'MUMPS', 'C: drive',
    'Modula-2', 'Modula-3', 'Oberon', 'Occam', 'OpenGL', 'parallel languages',
    'Pascal', 'Perl', 'PL/I', 'PostScript', 'Prolog', 'hardware', 'Blue Screen of Death',
    'Rexx', 'RPG', 'Scheme', 'scripting languages', 'Smalltalk', 'crash!', 'disc crash',
    'Spanner', 'SQL', 'Tcl/Tk', 'TeX', 'TOM', 'Visual', 'Visual Basic', '4GL',
    'VRML', 'Virtual Reality Modeling Language', 'difference engine', '...went into "yo-yo mode"',
    'Sun', 'Sun Microsystems', 'Hewlett Packard', 'output device',
    'CPU', 'memory', 'registers', 'monitor', 'TFT display', 'plasma screen',
    'bug report', '"mis-feature"', '...millions of bugs!', 'pizza',
    '"illiterate programming"','...lots of pizza!', 'pepperoni pizza',
    'coffee', 'Jolt Cola[TM]', 'beer', 'BEER!']

#theme three - 'blah' - for when you want to be subtle. :-)
BLAH = ['Blah', 'BLAH', 'blahblah', 'blahblahblah', 'blah-blah',
    'blah!', '"Blah Blah Blah"', 'blah-de-blah', 'blah?', 'blah!!!',
    'blah...', 'Blah.', 'blah;', 'blah, Blah, BLAH!', 'Blah!!!']

#theme four - 'buzzword bingo' time!
BUZZWORD = ['intellectual capital', 'market segment', 'flattening',
        'regroup', 'platform', 'client-based', 'long-term', 'proactive',
        'quality vector', 'out of the loop', 'implement',
        'streamline', 'cost-centered', 'phase', 'synergy',
        'synergize', 'interactive', 'facilitate',
        'appropriate', 'goal-setting', 'empowering', 'low-risk high-yield',
        'peel the onion', 'goal', 'downsize', 'result-driven',
        'conceptualize', 'multidisciplinary', 'gap analysis', 'dysfunctional',
        'networking', 'knowledge management', 'goal-setting',
        'mastery learning', 'communication', 'real-estate', 'quarterly',
        'scalable', 'Total Quality Management', 'best of breed',
        'nimble', 'monetize', 'benchmark', 'hardball',
        'client-centered', 'vision statement', 'empowerment',
        'lean & mean', 'credibility', 'synergistic',
        'backward-compatible', 'hardball', 'stretch the envelope',
        'bleeding edge', 'networking', 'motivation', 'best practice',
        'best of breed', 'implementation', 'Total Quality Management',
        'undefined', 'disintermediate', 'mindset', 'architect',
        'gap analysis', 'morale', 'objective', 'projection',
        'contribution', 'proactive', 'go the extra mile', 'dynamic',
        'world class', 'real estate', 'quality vector', 'credibility',
        'appropriate', 'platform', 'projection', 'mastery learning',
        'recognition', 'quality', 'scenario', 'performance based',
        'solutioning', 'go the extra mile', 'downsize', 'phase',
        'networking', 'experiencing slippage', 'knowledge management',
        'high priority', 'process', 'ethical', 'value-added', 'implement',
        're-factoring', 're-branding', 'embracing change']

#theme five - Star Trek
STARTREK = ['Starfleet', 'Klingon', 'Romulan', 'Cardassian', 'Vulcan',
    'Benzite', 'IKV Pagh', 'emergency transponder', 'United Federation of Planets',
    'Bolian', "K'Vort Class Bird-of-Prey", 'USS Enterprise', 'USS Intrepid',
    'USS Reliant', 'USS Voyager', 'Starfleet Academy', 'Captain Picard',
    'Captain Janeway', 'Tom Paris', 'Harry Kim', 'Counsellor Troi',
    'Lieutenant Worf', 'Lieutenant Commander Data', 'Dr. Beverly Crusher',
    'Admiral Nakamura', 'Irumodic Syndrome', 'Devron system', 'Admiral Pressman',
    'asteroid field', 'sensor readings', 'Binars', 'distress signal', 'shuttlecraft',
    'cloaking device', 'shuttle bay 2', 'Dr. Pulaski', 'Lwaxana Troi', 'Pacifica',
    'William Riker', "Chief O'Brian", 'Soyuz class science vessel', 'Wolf-359',
    'Galaxy class vessel', 'Utopia Planitia yards', 'photon torpedo', 'Archer IV',
    'quantum flux', 'spacedock', 'Risa', 'Deep Space Nine', 'blood wine',
    'quantum torpedoes', 'holodeck', 'Romulan Warbird', 'Betazoid', 'turbolift', 'battle bridge',
    'Memory Alpha', '...with a phaser!', 'Romulan ale', 'Ferrengi', 'Klingon opera',
    'Quark', 'wormhole', 'Bajoran', 'cruiser', 'warship', 'battlecruiser', '"Intruder alert!"',
    'scout ship', 'science vessel', '"Borg Invasion imminent!" ', '"Abandon ship!"',
    'Red Alert!', 'warp-core breech', '"All hands abandon ship! This is not a drill!"']

#theme six - print-related terms
PRINTING = ['points', 'picas', 'leading', 'kerning', 'CMYK', 'offset litho',
    'type', 'font family', 'typography', 'type designer',
    'baseline', 'white-out type', 'WOB', 'bicameral', 'bitmap',
    'blockletter', 'bleed', 'margin', 'body', 'widow', 'orphan',
    'cicero', 'cursive', 'letterform', 'sidehead', 'dingbat', 'leader',
    'DPI', 'drop-cap', 'paragraph', 'En', 'Em', 'flush left', 'left justified',
    'right justified', 'centered', 'italic', 'Latin letterform', 'ligature',
    'uppercase', 'lowercase', 'serif', 'sans-serif', 'weight', 'type foundry',
    'fleuron', 'folio', 'gutter', 'whitespace', 'humanist letterform', 'caption',
    'page', 'frame', 'ragged setting', 'flush-right', 'rule', 'drop shadows',
    'prepress', 'spot-colour', 'duotones', 'colour separations', 'four-colour printing',
    'Pantone[TM]', 'service bureau', 'imagesetter']

#it had to be done!...
#theme seven - the "full Monty"!
PYTHON = ['Good evening ladies and Bruces','I want to buy some cheese', 'You do have some cheese, do you?',
          "Of course sir, it's a cheese shop sir, we've got...",'discipline?... naked? ... With a melon!?',
          'The Church Police!!' , "There's a dead bishop on the landing", 'Would you like a twist of lemming sir?',
          '"Conquistador Coffee brings a new meaning to the word vomit"','Your lupins please',
          'Crelm Toothpaste, with the miracle ingredient Fraudulin',
          "Well there's the first result and the Silly Party has held Leicester.",
          'Hello, I would like to buy a fish license please', "Look, it's people like you what cause unrest!",
          "When we got home, our Dad would thrash us to sleep with his belt!", 'Luxury', "Gumby Brain Specialist",
          "My brain hurts!!!", "My brain hurts too.", "How not to be seen",
          "In this picture there are 47 people. None of them can be seen",
          "Mrs Smegma, will you stand up please?",
          "Mr. Nesbitt has learned the first lesson of 'Not Being Seen', not to stand up.",
          "My hovercraft is full of eels", "Ah. You have beautiful thighs.", "My nipples explode with delight",
          "Drop your panties Sir William, I cannot wait 'til lunchtime",
          "I'm a completely self-taught idiot.", "I always wanted to be a lumberjack!!!",
          "Told you so!! Oh, coitus!!", "",
          "Nudge nudge?", "Know what I mean!", "Nudge nudge, nudge nudge?", "Say no more!!",
          "Hello, well it's just after 8 o'clock, and time for the penguin on top of your television set to explode",
          "Oh, intercourse the penguin!!", "Funny that penguin being there, isn't it?",
          "I wish to register a complaint.", "Now that's what I call a dead parrot", "Pining for the fjords???",
          "No, that's not dead, it's ,uhhhh, resting", "This is an ex-parrot!!",
          "That parrot is definitely deceased.", "No, no, no - it's spelt Raymond Luxury Yach-t, but it's pronounced 'Throatwobbler Mangrove'.",
          "You're a very silly man and I'm not going to interview you.", "No Mungo... never kill a customer."
          "And I'd like to conclude by putting my finger up my nose",
          "egg and Spam", "egg bacon and Spam", "egg bacon sausage and Spam", "Spam bacon sausage and Spam",
          "Spam egg Spam Spam bacon and Spam", "Spam sausage Spam Spam Spam bacon Spam tomato and Spam",
          "Spam Spam Spam egg and Spam", "Spam Spam Spam Spam Spam Spam baked beans Spam Spam Spam",
          "Spam!!", "I don't like Spam!!!", "You can't have egg, bacon, Spam and sausage without the Spam!",
          "I'll have your Spam. I Love it!",
          "I'm having Spam Spam Spam Spam Spam Spam Spam baked beans Spam Spam Spam and Spam",
          "Have you got anything without Spam?", "There's Spam egg sausage and Spam, that's not got much Spam in it.",
          "No one expects the Spanish Inquisition!!", "Our weapon is surprise, surprise and fear!",
          "Get the comfy chair!", "Amongst our weaponry are such diverse elements as: fear, surprise, ruthless efficiency, an almost fanatical devotion to the Pope, and nice red uniforms - Oh damn!",
          "Nobody expects the... Oh bugger!", "What swims in the sea and gets caught in nets? Henri Bergson?",
          "Goats. Underwater goats with snorkels and flippers?", "A buffalo with an aqualung?",
          "Dinsdale was a looney, but he was a happy looney.", "Dinsdale!!",
          "The 127th Upper-Class Twit of the Year Show", "What a great Twit!",
          "thought by many to be this year's outstanding twit",
          "...and there's a big crowd here today to see these prize idiots in action.",
          "And now for something completely different.", "Stop that, it's silly",
          "We interrupt this program to annoy you and make things generally irritating",
          "This depraved and degrading spectacle is going to stop right now, do you hear me?",
          "Stop right there!", "This is absolutely disgusting and I'm not going to stand for it",
          "I object to all this sex on the television. I mean, I keep falling off",
          "Right! Stop that, it's silly. Very silly indeed", "Very silly indeed", "Lemon curry?",
          "And now for something completely different, a man with 3 buttocks",
          "I've heard of unisex, but I've never had it", "That's the end, stop the program! Stop it!"]
leadins=[
    "To characterize a linguistic level L,",
    "On the other hand,",
    "This suggests that",
    "It appears that",
    "Furthermore,",
    "We will bring evidence in favor of the following thesis: ",
    "To provide a constituent structure for T(Z,K),",
    "From C1, it follows that",
    "For any transformation which is sufficiently diversified in application to be of any interest,",
    "Analogously,",
    "Clearly,",
    "Note that",
    "Of course,",
    "Suppose, for instance, that",
    "Thus",
    "With this clarification,",
    "Conversely,",
    "We have already seen that",
    "By combining adjunctions and certain deformations,",
    "I suggested that these results would follow from the assumption that",
    "If the position of the trace in (99c) were only relatively inaccessible to movement,",
    "However, this assumption is not correct, since",
    "Comparing these examples with their parasitic gap counterparts in (96) and (97), we see that",
    "In the discussion of resumptive pronouns following (81),",
    "So far,",
    "Nevertheless,",
    "For one thing,",
    "Summarizing, then, we assume that",
    "A consequence of the approach just outlined is that",
    "Presumably,",
    "On our assumptions,",
    "It may be, then, that",
    "It must be emphasized, once again, that",
    "Let us continue to suppose that",
    "Notice, incidentally, that",
    "A majority  of informed linguistic specialists agree that",
    "There is also a different approach to the [unification] problem,",
    "This approach divorces the cognitive sciences from a biological setting,",
    "The approach relies on the \"Turing Test,\" devised by mathematician Alan Turing,",
    "Adopting this approach,",
    "There is no fact, no meaningful question to be answered,",
    "Another superficial similarity is the interest in simulation of behavior,",
    "A lot of sophistication has been developed about the utilization of machines for complex purposes,",
    ]
 
subjects = [
    "the notion of level of grammaticalness",
    "a case of semigrammaticalness of a different sort",
    "most of the methodological work in modern linguistics",
    "a subset of English sentences interesting on quite independent grounds",
    "the natural general principle that will subsume this case",
    "an important property of these three types of EC",
    "any associated supporting element",
    "the appearance of parasitic gaps in domains relatively inaccessible to ordinary extraction",
    "the speaker-hearer's linguistic intuition",
    "the descriptive power of the base component",
    "the earlier discussion of deviance",
    "this analysis of a formative as a pair of sets of features",
    "this selectionally introduced contextual feature",
    "a descriptively adequate grammar",
    "the fundamental error of regarding functional notions as categorial",
    "relational information",
    "the systematic use of complex symbols",
    "the theory of syntactic features developed earlier",
    ]
 
verbs= [
    "can be defined in such a way as to impose",
    "delimits",
    "suffices to account for",
    "cannot be arbitrary in",
    "is not subject to",
    "does not readily tolerate",
    "raises serious doubts about",
    "is not quite equivalent to",
    "does not affect the structure of",
    "may remedy and, at the same time, eliminate",
    "is not to be considered in determining",
    "is to be regarded as",
    "is unspecified with respect to",
    "is, apparently, determined by",
    "is necessary to impose an interpretation on",
    "appears to correlate rather closely with",
    "is rather different from",
    ]

objects = [
    "problems of phonemic and morphological analysis.",
    "a corpus of utterance tokens upon which conformity has been defined by the paired utterance test.",
    "the traditional practice of grammarians.",
    "the levels of acceptability from fairly high (e.g. (99a)) to virtual gibberish (e.g. (98d)).",
    "a stipulation to place the constructions into these various categories.",
    "a descriptive fact.",
    "a parasitic gap construction.",
    "the extended c-command discussed in connection with (34).",
    "the ultimate standard that determines the accuracy of any proposed grammar.",
    "the system of base rules exclusive of the lexicon.",
    "irrelevant intervening contexts in selectional rules.",
    "nondistinctness in the sense of distinctive feature theory.",
    "a general convention regarding the forms of the grammar.",
    "an abstract underlying order.",
    "an important distinction in language use.",
    "the requirement that branching is not tolerated within the dominance scope of a complex symbol.",
    "the strong generative capacity of the theory.",
    ]

def format_wisdom(text,line_length=72):
    try:
        import textwrap
        return textwrap.fill(text, line_length)
    except:
        return text

def chomsky(times = 1):
    if not isinstance(times, int):
        return format_wisdom(__doc__)
    import random
    prevparts = []
    newparts = []
    output = []
    for i in range(times):
        for partlist in (leadins, subjects, verbs, objects):
            while 1:
                part = random.choice(partlist)
                if part not in prevparts:
                    break
            newparts.append(part)
        output.append(' '.join(newparts))
        prevparts = newparts
        newparts = []
    return format_wisdom('  '.join(output))

from reportlab import rl_config
if rl_config.invariant:
    import random
    #monkey patch random.randrange
    class RLMonkeyPatchRandom(random.Random):
        def randrange(self, start, stop=None, step=1, _int=int, _maxwidth=1<<random.BPF):
            """Choose a random item from range(start, stop[, step]).

            This fixes the problem with randint() which includes the
            endpoint; in Python this is usually not what you want.

            """

            # This code is a bit messy to make it fast for the
            # common case while still doing adequate error checking.
            istart = _int(start)
            if istart != start:
                raise ValueError("non-integer arg 1 for randrange()")
            if stop is None:
                if istart > 0:
                    if istart >= _maxwidth:
                        return self._randbelow(istart)
                    return _int(self.random() * istart)
                raise ValueError("empty range for randrange()")

            # stop argument supplied.
            istop = _int(stop)
            if istop != stop:
                raise ValueError("non-integer stop for randrange()")
            width = istop - istart
            if step == 1 and width > 0:
                # Note that
                #     int(istart + self.random()*width)
                # instead would be incorrect.  For example, consider istart
                # = -2 and istop = 0.  Then the guts would be in
                # -2.0 to 0.0 exclusive on both ends (ignoring that random()
                # might return 0.0), and because int() truncates toward 0, the
                # final result would be -1 or 0 (instead of -2 or -1).
                #     istart + int(self.random()*width)
                # would also be incorrect, for a subtler reason:  the RHS
                # can return a long, and then randrange() would also return
                # a long, but we're supposed to return an int (for backward
                # compatibility).

                if width >= _maxwidth:
                    return _int(istart + self._randbelow(width))
                return _int(istart + _int(self.random()*width))
            if step == 1:
                raise ValueError("empty range for randrange() (%d,%d, %d)" % (istart, istop, width))

            # Non-unit step argument supplied.
            istep = _int(step)
            if istep != step:
                raise ValueError("non-integer step for randrange()")
            if istep > 0:
                n = (width + istep - 1) // istep
            elif istep < 0:
                n = (width + istep + 1) // istep
            else:
                raise ValueError("zero step for randrange()")

            if n <= 0:
                raise ValueError("empty range for randrange()")

            if n >= _maxwidth:
                return istart + istep*self._randbelow(n)
            return istart + istep*_int(self.random() * n)
        def choice(self, seq):
            """Choose a random element from a non-empty sequence."""
            return seq[int(self.random() * len(seq))]
    random.Random.randrange = RLMonkeyPatchRandom.randrange
    random.Random.choice = RLMonkeyPatchRandom.choice
    random.randrange = random._inst.randrange
    random.choice = random._inst.choice
    del RLMonkeyPatchRandom
    if not getattr(rl_config,'_random',None):
        rl_config._random = 1
        random.seed(2342471922)
    del random
del rl_config

def randomText(theme=STARTUP, sentences=5):
    #this may or may not be appropriate in your company
    if type(theme)==type(''):
        if theme.lower()=='chomsky': return chomsky(sentences)
        elif theme.upper() in ('STARTUP','COMPUTERS','BLAH','BUZZWORD','STARTREK','PRINTING','PYTHON'):
            theme = globals()[theme.upper()]
        else:
            raise ValueError('Unknown theme "%s"' % theme)

    from random import randint, choice

    RANDOMWORDS = theme

    #sentences = 5
    output = ""
    for sentenceno in range(randint(1,sentences)):
        output = output + 'Blah'
        for wordno in range(randint(10,25)):
            if randint(0,4)==0:
                word = choice(RANDOMWORDS)
            else:
                word = 'blah'
            output = output + ' ' +word
        output = output+'. '
    return output

if __name__=='__main__':
    import sys
    argv = sys.argv[1:]
    if argv:
        theme = argv.pop(0)
        if argv:
            sentences = int(argv.pop(0))
        else:
            sentences = 5
        try:
            print(randomText(theme,sentences))
        except:
            sys.stderr.write("Usage: randomtext.py [theme [#sentences]]\n")
            sys.stderr.write(" theme in chomsky|STARTUP|COMPUTERS|BLAH|BUZZWORD|STARTREK|PRINTING|PYTHON\n")
            raise
    else:
        print(chomsky(5))
