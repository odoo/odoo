#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/xpreformatted.py
__version__=''' $Id: xpreformatted.py 2426 2004-09-02 11:52:56Z rgbecker $ '''

import string
from types import StringType, ListType

from reportlab.lib import PyFontify
from paragraph import Paragraph, cleanBlockQuotedText, _handleBulletWidth, \
     ParaLines, _getFragWords, stringWidth, _sameFrag
from flowables import _dedenter


def _getFragLines(frags):
    lines = []
    cline = []
    W = frags[:]
    while W != []:
        w = W[0]
        t = w.text
        del W[0]
        i = string.find(t,'\n')
        if i>=0:
            tleft = t[i+1:]
            cline.append(w.clone(text=t[:i]))
            lines.append(cline)
            cline = []
            if tleft!='':
                W.insert(0,w.clone(text=tleft))
        else:
            cline.append(w)
    if cline!=[]:
        lines.append(cline)
    return lines

def _split_blPara(blPara,start,stop):
    f = blPara.clone()
    for a in ('lines', 'text'):
        if hasattr(f,a): delattr(f,a)
    f.lines = blPara.lines[start:stop]
    return [f]

# Will be removed shortly.
def _countSpaces(text):
    return string.count(text, ' ')
##  i = 0
##  s = 0
##  while 1:
##      j = string.find(text,' ',i)
##      if j<0: return s
##      s = s + 1
##      i = j + 1

def _getFragWord(frags):
    ''' given a fragment list return a list of lists
        [size, spaces, (f00,w00), ..., (f0n,w0n)]
        each pair f,w represents a style and some string
    '''
    W = []
    n = 0
    s = 0
    for f in frags:
        text = f.text[:]
        W.append((f,text))
        n = n + stringWidth(text, f.fontName, f.fontSize)

        #s = s + _countSpaces(text)
        s = s + string.count(text, ' ') # much faster for many blanks

        #del f.text # we can't do this until we sort out splitting
                    # of paragraphs
    return n, s, W


class XPreformatted(Paragraph):
    def __init__(self, text, style, bulletText = None, frags=None, caseSensitive=1, dedent=0):
        self.caseSensitive = caseSensitive
        cleaner = lambda text, dedent=dedent: string.join(_dedenter(text or '',dedent),'\n')
        self._setup(text, style, bulletText, frags, cleaner)

    def breakLines(self, width):
        """
        Returns a broken line structure. There are two cases

        A) For the simple case of a single formatting input fragment the output is
            A fragment specifier with
                kind = 0
                fontName, fontSize, leading, textColor
                lines=  A list of lines
                        Each line has two items.
                        1) unused width in points
                        2) a list of words

        B) When there is more than one input formatting fragment the out put is
            A fragment specifier with
                kind = 1
                lines=  A list of fragments each having fields
                            extraspace (needed for justified)
                            fontSize
                            words=word list
                                each word is itself a fragment with
                                various settings

        This structure can be used to easily draw paragraphs with the various alignments.
        You can supply either a single width or a list of widths; the latter will have its
        last item repeated until necessary. A 2-element list is useful when there is a
        different first line indent; a longer list could be created to facilitate custom wraps
        around irregular objects."""

        if type(width) <> ListType: maxWidths = [width]
        else: maxWidths = width
        lines = []
        lineno = 0
        maxWidth = maxWidths[lineno]
        style = self.style
        fFontSize = float(style.fontSize)
        requiredWidth = 0

        #for bullets, work out width and ensure we wrap the right amount onto line one
        _handleBulletWidth(self.bulletText,style,maxWidths)

        self.height = 0
        frags = self.frags
        nFrags= len(frags)
        if nFrags==1:
            f = frags[0]
            if hasattr(f,'text'):
                fontSize = f.fontSize
                fontName = f.fontName
                kind = 0
                L=string.split(f.text, '\n')
                for l in L:
                    currentWidth = stringWidth(l,fontName,fontSize)
                    requiredWidth = max(currentWidth,requiredWidth)
                    extraSpace = maxWidth-currentWidth
                    lines.append((extraSpace,string.split(l,' '),currentWidth))
                    lineno = lineno+1
                    maxWidth = lineno<len(maxWidths) and maxWidths[lineno] or maxWidths[-1]
            else:
                kind = f.kind
                lines = f.lines
                for L in lines:
                    if kind==0:
                        currentWidth = L[2]
                    else:
                        currentWidth = L.currentWidth
                    requiredWidth = max(currentWidth,requiredWidth)

            self.width = max(self.width,requiredWidth)
            return f.clone(kind=kind, lines=lines)
        elif nFrags<=0:
            return ParaLines(kind=0, fontSize=style.fontSize, fontName=style.fontName,
                            textColor=style.textColor, lines=[])
        else:
            for L in _getFragLines(frags):
                maxSize = 0
                currentWidth, n, w = _getFragWord(L)
                f = w[0][0]
                maxSize = max(maxSize,f.fontSize)
                words = [f.clone()]
                words[-1].text = w[0][1]
                for i in w[1:]:
                    f = i[0].clone()
                    f.text=i[1]
                    words.append(f)
                    maxSize = max(maxSize,f.fontSize)

                lineno = lineno+1
                maxWidth = lineno<len(maxWidths) and maxWidths[lineno] or maxWidths[-1]
                requiredWidth = max(currentWidth,requiredWidth)
                extraSpace = maxWidth - currentWidth
                lines.append(ParaLines(extraSpace=extraSpace,wordCount=n, words=words, fontSize=maxSize, currentWidth=currentWidth))

            self.width = max(self.width,requiredWidth)
            return ParaLines(kind=1, lines=lines)

        return lines

    # we need this her to get the right splitter
    def _get_split_blParaFunc(self):
        return _split_blPara


class PythonPreformatted(XPreformatted):
    """Used for syntax-colored Python code, otherwise like XPreformatted.
    """

    formats = {
        'rest'       : ('', ''),
        'comment'    : ('<font color="green">', '</font>'),
        'keyword'    : ('<font color="blue"><b>', '</b></font>'),
        'parameter'  : ('<font color="black">', '</font>'),
        'identifier' : ('<font color="red">', '</font>'),
        'string'     : ('<font color="gray">', '</font>') }

    def __init__(self, text, style, bulletText = None, dedent=0, frags=None):
        if text:
            text = self.fontify(self.escapeHtml(text))
        apply(XPreformatted.__init__,
              (self, text, style),
              {'bulletText':bulletText, 'dedent':dedent, 'frags':frags})

    def escapeHtml(self, text):
        s = string.replace(text, '&', '&amp;')
        s = string.replace(s, '<', '&lt;')
        s = string.replace(s, '>', '&gt;')
        return s

    def fontify(self, code):
        "Return a fontified version of some Python code."

        if code[0] == '\n':
            code = code[1:]

        tags = PyFontify.fontify(code)
        fontifiedCode = ''
        pos = 0
        for k, i, j, dummy in tags:
            fontifiedCode = fontifiedCode + code[pos:i]
            s, e = self.formats[k]
            fontifiedCode = fontifiedCode + s + code[i:j] + e
            pos = j

        fontifiedCode = fontifiedCode + code[pos:]

        return fontifiedCode


if __name__=='__main__':    #NORUNTESTS
    def dumpXPreformattedLines(P):
        print '\n############dumpXPreforemattedLines(%s)' % str(P)
        lines = P.blPara.lines
        n =len(lines)
        for l in range(n):
            line = lines[l]
            words = line.words
            nwords = len(words)
            print 'line%d: %d(%d)\n  ' % (l,nwords,line.wordCount),
            for w in range(nwords):
                print "%d:'%s'"%(w,words[w].text),
            print

    def dumpXPreformattedFrags(P):
        print '\n############dumpXPreforemattedFrags(%s)' % str(P)
        frags = P.frags
        n =len(frags)
        for l in range(n):
            print "frag%d: '%s'" % (l, frags[l].text)

        l = 0
        for L in _getFragLines(frags):
            n=0
            for W in _getFragWords(L):
                print "frag%d.%d: size=%d" % (l, n, W[0]),
                n = n + 1
                for w in W[1:]:
                    print "'%s'" % w[1],
                print
            l = l + 1

    def try_it(text,style,dedent,aW,aH):
        P=XPreformatted(text,style,dedent=dedent)
        dumpXPreformattedFrags(P)
        w,h = P.wrap(aW, aH)
        dumpXPreformattedLines(P)
        S = P.split(aW,aH)
        dumpXPreformattedLines(P)
        for s in S:
            s.wrap(aW,aH)
            dumpXPreformattedLines(s)
            aH = 500

    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    styleSheet = getSampleStyleSheet()
    B = styleSheet['BodyText']
    DTstyle = ParagraphStyle("discussiontext", parent=B)
    DTstyle.fontName= 'Helvetica'
    for (text,dedent,style, aW, aH, active) in [('''


The <font name=courier color=green>CMYK</font> or subtractive

method follows the way a printer
mixes three pigments (cyan, magenta, and yellow) to form colors.
Because mixing chemicals is more difficult than combining light there
is a fourth parameter for darkness.  For example a chemical
combination of the <font name=courier color=green>CMY</font> pigments generally never makes a perfect

black -- instead producing a muddy color -- so, to get black printers
don't use the <font name=courier color=green>CMY</font> pigments but use a direct black ink.  Because
<font name=courier color=green>CMYK</font> maps more directly to the way printer hardware works it may
be the case that &amp;| &amp; | colors specified in <font name=courier color=green>CMYK</font> will provide better fidelity
and better control when printed.


''',0,DTstyle, 456.0, 42.8, 0),
('''

   This is a non rearranging form of the <b>Paragraph</b> class;
   <b><font color=red>XML</font></b> tags are allowed in <i>text</i> and have the same

      meanings as for the <b>Paragraph</b> class.
   As for <b>Preformatted</b>, if dedent is non zero <font color=red size=+1>dedent</font>
       common leading spaces will be removed from the
   front of each line.

''',3, DTstyle, 456.0, 42.8, 0),
("""\
    <font color=blue>class </font><font color=red>FastXMLParser</font>:
        # Nonsense method
        def nonsense(self):
            self.foo = 'bar'
""",0, styleSheet['Code'], 456.0, 4.8, 1),
]:
        if active: try_it(text,style,dedent,aW,aH)
