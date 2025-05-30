#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__='3.3.0'
__doc__="""A Sequencer class counts things. It aids numbering and formatting lists."""
__all__='''Sequencer getSequencer setSequencer'''.split()
#
# roman numbers conversion thanks to
#
# fredrik lundh, november 1996 (based on a C hack from 1984)
#
# fredrik@pythonware.com
# http://www.pythonware.com

_RN_TEMPLATES = [ 0, 0o1, 0o11, 0o111, 0o12, 0o2, 0o21, 0o211, 0o2111, 0o13 ]
_RN_LETTERS = "IVXLCDM"

def _format_I(value):
    if value < 0 or value > 3999:
        raise ValueError("illegal value")
    str = ""
    base = -1
    while value:
        value, index = divmod(value, 10)
        tmp = _RN_TEMPLATES[index]
        while tmp:
            tmp, index = divmod(tmp, 8)
            str = _RN_LETTERS[index+base] + str
        base += 2
    return str

def _format_i(num):
    return _format_I(num).lower()

def _format_123(num):
    """The simplest formatter"""
    return str(num)

def _format_ABC(num):
    """Uppercase.  Wraps around at 26."""
    n = (num -1) % 26
    return chr(n+65)

def _format_abc(num):
    """Lowercase.  Wraps around at 26."""
    n = (num -1) % 26
    return chr(n+97)

_type2formatter = {
        'I':_format_I,
        'i':_format_i,
        '1':_format_123,
        'A':_format_ABC,
        'a':_format_abc,
        }

class _Counter:
    """Private class used by Sequencer.  Each counter
    knows its format, and the IDs of anything it
    resets, as well as its value. Starts at zero
    and increments just before you get the new value,
    so that it is still 'Chapter 5' and not 'Chapter 6'
    when you print 'Figure 5.1'"""

    def __init__(self):
        self._base = 0
        self._value = self._base
        self._formatter = _format_123
        self._resets = []

    def setFormatter(self, formatFunc):
        self._formatter = formatFunc

    def reset(self, value=None):
        if value:
            self._value = value
        else:
            self._value = self._base

    def next(self):
        self._value += 1
        v = self._value
        for counter in self._resets:
            counter.reset()
        return v
    __next__ = next

    def _this(self):
        return self._value

    def nextf(self):
        """Returns next value formatted"""
        return self._formatter(next(self))

    def thisf(self):
        return self._formatter(self._this())

    def chain(self, otherCounter):
        if not otherCounter in self._resets:
            self._resets.append(otherCounter)

class Sequencer:
    """Something to make it easy to number paragraphs, sections,
    images and anything else.  The features include registering
    new string formats for sequences, and 'chains' whereby
    some counters are reset when their parents.
    It keeps track of a number of
    'counters', which are created on request:
    Usage::
    
        >>> seq = layout.Sequencer()
        >>> seq.next('Bullets')
        1
        >>> seq.next('Bullets')
        2
        >>> seq.next('Bullets')
        3
        >>> seq.reset('Bullets')
        >>> seq.next('Bullets')
        1
        >>> seq.next('Figures')
        1
        >>>
    """

    def __init__(self):
        self._counters = {}  #map key to current number
        self._formatters = {}
        self._reset()

    def _reset(self):
        self._counters.clear()
        self._formatters.clear()
        self._formatters.update({
            # the formats it knows initially
            '1':_format_123,
            'A':_format_ABC,
            'a':_format_abc,
            'I':_format_I,
            'i':_format_i,
            })
        d = dict(_counters=self._counters,_formatters=self._formatters)
        self.__dict__.clear()
        self.__dict__.update(d)
        self._defaultCounter = None

    def _getCounter(self, counter=None):
        """Creates one if not present"""
        try:
            return self._counters[counter]
        except KeyError:
            cnt = _Counter()
            self._counters[counter] = cnt
            return cnt

    def _this(self, counter=None):
        """Retrieves counter value but does not increment. For
        new counters, sets base value to 1."""
        if not counter:
            counter = self._defaultCounter
        return self._getCounter(counter)._this()

    def __next__(self):
        """Retrieves the numeric value for the given counter, then
        increments it by one.  New counters start at one."""
        return next(self._getCounter(self._defaultCounter))

    def next(self,counter=None):
        if not counter:
            return next(self)
        else:
            dc = self._defaultCounter
            try:
                self._defaultCounter = counter
                return next(self)
            finally:
                self._defaultCounter = dc

    def thisf(self, counter=None):
        if not counter:
            counter = self._defaultCounter
        return self._getCounter(counter).thisf()

    def nextf(self, counter=None):
        """Retrieves the numeric value for the given counter, then
        increments it by one.  New counters start at one."""
        if not counter:
            counter = self._defaultCounter
        return self._getCounter(counter).nextf()

    def setDefaultCounter(self, default=None):
        """Changes the key used for the default"""
        self._defaultCounter = default

    def registerFormat(self, format, func):
        """Registers a new formatting function.  The funtion
        must take a number as argument and return a string;
        fmt is a short menmonic string used to access it."""
        self._formatters[format] = func

    def setFormat(self, counter, format):
        """Specifies that the given counter should use
        the given format henceforth."""
        func = self._formatters[format]
        self._getCounter(counter).setFormatter(func)

    def reset(self, counter=None, base=0):
        if not counter:
            counter = self._defaultCounter
        self._getCounter(counter)._value = base

    def chain(self, parent, child):
        p = self._getCounter(parent)
        c = self._getCounter(child)
        p.chain(c)

    def __getitem__(self, key):
        """Allows compact notation to support the format function.
        s['key'] gets current value, s['key+'] increments."""
        if key[-1:] == '+':
            counter = key[:-1]
            return self.nextf(counter)
        else:
            return self.thisf(key)

    def format(self, template):
        """The crowning jewels - formats multi-level lists."""
        return template % self

    def dump(self):
        """Write current state to stdout for diagnostics"""
        counters = list(self._counters.items())
        counters.sort()
        print('Sequencer dump:')
        for (key, counter) in counters:
            print('    %s: value = %d, base = %d, format example = %s' % (
                key, counter._this(), counter._base, counter.thisf()))

"""Your story builder needs to set this to"""
_sequencer = None

def getSequencer():
    global _sequencer
    if _sequencer is None:
        _sequencer = Sequencer()
    return  _sequencer

def setSequencer(seq):
    global _sequencer
    s = _sequencer
    _sequencer = seq
    return s

def _reset():
    global _sequencer
    if _sequencer:
        _sequencer._reset()

from reportlab.rl_config import register_reset
register_reset(_reset)
del register_reset

def test():
    s = Sequencer()
    print('Counting using default sequence: %d %d %d' % (next(s),next(s), next(s)))
    print('Counting Figures: Figure %d, Figure %d, Figure %d' % (
        s.next('figure'), s.next('figure'), s.next('figure')))
    print('Back to default again: %d' % next(s))
    s.setDefaultCounter('list1')
    print('Set default to list1: %d %d %d' % (next(s),next(s), next(s)))
    s.setDefaultCounter()
    print('Set default to None again: %d %d %d' % (next(s),next(s), next(s)))
    print()
    print('Creating Appendix counter with format A, B, C...')
    s.setFormat('Appendix', 'A')
    print('    Appendix %s, Appendix %s, Appendix %s' % (
        s.nextf('Appendix'),    s.nextf('Appendix'),s.nextf('Appendix')))

    def format_french(num):
        return ('un','deux','trois','quatre','cinq')[(num-1)%5]
    print()
    print('Defining a custom format with french words:')
    s.registerFormat('french', format_french)
    s.setFormat('FrenchList', 'french')
    print('   ' +(' '.join(str(s.nextf('FrenchList')) for i in range(1,6))))
    print()
    print('Chaining H1 and H2 - H2 goes back to one when H1 increases')
    s.chain('H1','H2')
    print('    H1 = %d' % s.next('H1'))
    print('      H2 = %d' % s.next('H2'))
    print('      H2 = %d' % s.next('H2'))
    print('      H2 = %d' % s.next('H2'))
    print('    H1 = %d' % s.next('H1'))
    print('      H2 = %d' % s.next('H2'))
    print('      H2 = %d' % s.next('H2'))
    print('      H2 = %d' % s.next('H2'))
    print()
    print('GetItem notation - append a plus to increment')
    print('    seq["Appendix"] = %s' % s["Appendix"])
    print('    seq["Appendix+"] = %s' % s["Appendix+"])
    print('    seq["Appendix+"] = %s' % s["Appendix+"])
    print('    seq["Appendix"] = %s' % s["Appendix"])
    print()
    print('Finally, string format notation for nested lists.  Cool!')
    print('The expression ("Figure %(Chapter)s.%(Figure+)s" % seq) gives:')
    print('    Figure %(Chapter)s.%(Figure+)s' % s)
    print('    Figure %(Chapter)s.%(Figure+)s' % s)
    print('    Figure %(Chapter)s.%(Figure+)s' % s)


if __name__=='__main__':
    test()
