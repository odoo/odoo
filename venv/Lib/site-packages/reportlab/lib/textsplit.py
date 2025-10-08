#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/textsplit.py

"""Helpers for text wrapping, hyphenation, Asian text splitting and kinsoku shori.

How to split a 'big word' depends on the language and the writing system.  This module
works on a Unicode string.  It ought to grow by allowing ore algoriths to be plugged
in based on possible knowledge of the language and desirable 'niceness' of the algorithm.

"""

__version__='3.3.0'

from unicodedata import category
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import _FUZZ
from reportlab.lib.utils import isUnicode

CANNOT_START_LINE = [
    #strongly prohibited e.g. end brackets, stop, exclamation...
    u'!\',.:;?!")]\u3001\u3002\u300d\u300f\u3011\u3015\uff3d\u3011\uff09',
    #middle priority e.g. continuation small vowels - wrapped on two lines but one string...
    u'\u3005\u2015\u3041\u3043\u3045\u3047\u3049\u3063\u3083\u3085\u3087\u308e\u30a1\u30a3'
    u'\u30a5\u30a7\u30a9\u30c3\u30e3\u30e5\u30e7\u30ee\u30fc\u30f5\u30f6',
    #weakly prohibited - continuations, celsius symbol etc.
    u'\u309b\u309c\u30fb\u30fd\u30fe\u309d\u309e\u2015\u2010\xb0\u2032\u2033\u2103\uffe0\uff05\u2030'
    ]

ALL_CANNOT_START = u''.join(CANNOT_START_LINE)
CANNOT_END_LINE = [
    #strongly prohibited
    u'\u2018\u201c\uff08[{\uff08\u3014\uff3b\uff5b\u3008\u300a\u300c\u300e\u3010',
    #weaker - currency symbols, hash, postcode - prefixes
    u'$\u00a3@#\uffe5\uff04\uffe1\uff20\u3012\u00a7'
    ]
ALL_CANNOT_END = u''.join(CANNOT_END_LINE)

def is_multi_byte(ch):
    "Is this an Asian character?"
    return (ord(ch) >= 0x3000)
    
def getCharWidths(word, fontName, fontSize):
    """Returns a list of glyph widths.

    >>> getCharWidths('Hello', 'Courier', 10)
    [6.0, 6.0, 6.0, 6.0, 6.0]
    >>> from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    >>> from reportlab.pdfbase.pdfmetrics import registerFont
    >>> registerFont(UnicodeCIDFont('HeiseiMin-W3'))
    >>> getCharWidths(u'\u6771\u4EAC', 'HeiseiMin-W3', 10)   #most kanji are 100 ems
    [10.0, 10.0]
    """
    #character-level function call; the performance is going to SUCK

    return [stringWidth(uChar, fontName, fontSize) for uChar in word]

def wordSplit(word, maxWidths, fontName, fontSize, encoding='utf8'):
    """Attempts to break a word which lacks spaces into two parts, the first of which
    fits in the remaining space.  It is allowed to add hyphens or whatever it wishes.

    This is intended as a wrapper for some language- and user-choice-specific splitting
    algorithms.  It should only be called after line breaking on spaces, which covers western
    languages and is highly optimised already.  It works on the 'last unsplit word'.

    Presumably with further study one could write a Unicode splitting algorithm for text
    fragments whick was much faster.

    Courier characters should be 6 points wide.
    >>> wordSplit('HelloWorld', 30, 'Courier', 10)
    [[0.0, 'Hello'], [0.0, 'World']]
    >>> wordSplit('HelloWorld', 31, 'Courier', 10)
    [[1.0, 'Hello'], [1.0, 'World']]
    """
    if not isUnicode(word):
        uword = word.decode(encoding)
    else:
        uword = word

    charWidths = getCharWidths(uword, fontName, fontSize)
    lines = dumbSplit(uword, charWidths, maxWidths)

    if not isUnicode(word):
        lines2 = []
        #convert back
        for (extraSpace, text) in lines:
            lines2.append([extraSpace, text.encode(encoding)])
        lines = lines2

    return lines

def dumbSplit(word, widths, maxWidths):
    """This function attempts to fit as many characters as possible into the available
    space, cutting "like a knife" between characters.  This would do for Chinese.
    It returns a list of (text, extraSpace) items where text is a Unicode string,
    and extraSpace is the points of unused space available on the line.  This is a
    structure which is fairly easy to display, and supports 'backtracking' approaches
    after the fact.

    Test cases assume each character is ten points wide...

    >>> dumbSplit(u'Hello', [10]*5, 60)
    [[10, u'Hello']]
    >>> dumbSplit(u'Hello', [10]*5, 50)
    [[0, u'Hello']]
    >>> dumbSplit(u'Hello', [10]*5, 40)
    [[0, u'Hell'], [30, u'o']]
    """
    _more = """
    #>>> dumbSplit(u'Hello', [10]*5, 4)   # less than one character
    #(u'', u'Hello')
    # this says 'Nihongo wa muzukashii desu ne!' (Japanese is difficult isn't it?) in 12 characters
    >>> jtext = u'\u65e5\u672c\u8a9e\u306f\u96e3\u3057\u3044\u3067\u3059\u306d\uff01'
    >>> dumbSplit(jtext, [10]*11, 30)   #
    (u'\u65e5\u672c\u8a9e', u'\u306f\u96e3\u3057\u3044\u3067\u3059\u306d\uff01')
    """
    if not isinstance(maxWidths,(list,tuple)): maxWidths = [maxWidths]
    assert isUnicode(word)
    lines = []
    i = widthUsed = lineStartPos = 0
    maxWidth = maxWidths[0]
    nW = len(word)
    while i<nW:
        w = widths[i]
        c = word[i]
        widthUsed += w
        i += 1
        if widthUsed > maxWidth + _FUZZ and widthUsed>0:
            extraSpace = maxWidth - widthUsed
            if ord(c)<0x3000:
                # we appear to be inside a non-Asian script section.
                # (this is a very crude test but quick to compute).
                # This is likely to be quite rare so the speed of the
                # code below is hopefully not a big issue.  The main
                # situation requiring this is that a document title
                # with an english product name in it got cut.
                
                
                # we count back and look for 
                #  - a space-like character
                #  - reversion to Kanji (which would be a good split point)
                #  - in the worst case, roughly half way back along the line
                limitCheck = (lineStartPos+i)>>1        #(arbitrary taste issue)
                for j in range(i-1,limitCheck,-1):
                    cj = word[j]
                    if category(cj)=='Zs' or ord(cj)>=0x3000:
                        k = j+1
                        if k<i:
                            j = k+1
                            extraSpace += sum(widths[j:i])
                            w = widths[k]
                            c = word[k]
                            i = j
                            break

                #end of English-within-Asian special case

            #we are pushing this character back, but
            #the most important of the Japanese typography rules
            #if this character cannot start a line, wrap it up to this line so it hangs
            #in the right margin. We won't do two or more though - that's unlikely and
            #would result in growing ugliness.
            #and increase the extra space
            #bug fix contributed by Alexander Vasilenko <alexs.vasilenko@gmail.com>
            if c not in ALL_CANNOT_START and i>lineStartPos+1:
                #otherwise we need to push the character back
                #the i>lineStart+1 condition ensures progress
                i -= 1
                extraSpace += w

            #lines.append([maxWidth-sum(widths[lineStartPos:i]), word[lineStartPos:i].strip()])
            lines.append([extraSpace, word[lineStartPos:i].strip()])
            try:
                maxWidth = maxWidths[len(lines)]
            except IndexError:
                maxWidth = maxWidths[-1]  # use the last one
            lineStartPos = i
            widthUsed = 0

    #any characters left?
    if widthUsed > 0:
        lines.append([maxWidth - widthUsed, word[lineStartPos:]])

    return lines

def kinsokuShoriSplit(word, widths, availWidth):
    #NOT USED OR FINISHED YET!
    """Split according to Japanese rules according to CJKV (Lunde).

    Essentially look for "nice splits" so that we don't end a line
    with an open bracket, or start one with a full stop, or stuff like
    that.  There is no attempt to try to split compound words into
    constituent kanji.  It currently uses wrap-down: packs as much
    on a line as possible, then backtracks if needed

    This returns a number of words each of which should just about fit
    on a line.  If you give it a whole paragraph at once, it will
    do all the splits.

    It's possible we might slightly step over the width limit
    if we do hanging punctuation marks in future (e.g. dangle a Japanese
    full stop in the right margin rather than using a whole character
    box.

    """
    lines = []
    assert len(word) == len(widths)
    curWidth = 0.0
    curLine = []
    i = 0   #character index - we backtrack at times so cannot use for loop
    while 1:
        ch = word[i]
        w = widths[i]
        if curWidth + w < availWidth:
            curLine.append(ch)
            curWidth += w
        else:
            #end of line.  check legality
            if ch in CANNOT_END_LINE[0]:
                pass
    #to be completed

# This recipe refers:
#
#  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
import re
rx=re.compile("([\u2e80-\uffff])", re.UNICODE)
def cjkwrap(text, width, encoding="utf8"):
     return reduce(lambda line, word, width=width: '%s%s%s' %
                (line,
                 [' ','\n', ''][(len(line)-line.rfind('\n')-1
                       + len(word.split('\n',1)[0] ) >= width) or
                      line[-1:] == '\0' and 2],
                 word),
                rx.sub(r'\1\0 ', str(text,encoding)).split(' ')
            ).replace('\0', '').encode(encoding)

if __name__=='__main__':
    import doctest
    from reportlab.lib import textsplit
    doctest.testmod(textsplit)
