#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/tableofcontents.py

__version__='4.2.1.1'
__doc__="""Experimental class to generate Tables of Contents easily

This module defines a single TableOfContents() class that can be used to
create automatically a table of tontents for Platypus documents like
this:

    story = []
    toc = TableOfContents()
    story.append(toc)
    # some heading paragraphs here...
    doc = MyTemplate(path)
    doc.multiBuild(story)

The data needed to create the table is a list of (level, text, pageNum)
triplets, plus some paragraph styles for each level of the table itself.
The triplets will usually be created in a document template's method
like afterFlowable(), making notification calls using the notify()
method with appropriate data like this:

    (level, text, pageNum) = ...
    self.notify('TOCEntry', (level, text, pageNum))

Optionally the list can contain four items in which case the last item
is a destination key which the entry should point to. A bookmark
with this key needs to be created first like this:

    key = 'ch%s' % self.seq.nextf('chapter')
    self.canv.bookmarkPage(key)
    self.notify('TOCEntry', (level, text, pageNum, key))

As the table of contents need at least two passes over the Platypus
story which is why the multiBuild() method must be called.

The level<NUMBER>ParaStyle variables are the paragraph styles used
to format the entries in the table of contents. Their indentation
is calculated like this: each entry starts at a multiple of some
constant named delta. If one entry spans more than one line, all
lines after the first are indented by the same constant named
epsilon.
"""

from reportlab.lib.units import cm
from reportlab.lib.utils import commasplit, escapeOnce, encode_label, decode_label, strTypes, asUnicode, asNative
from reportlab.lib.styles import ParagraphStyle, _baseFontName
from reportlab.lib import sequencer as rl_sequencer
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.doctemplate import IndexingFlowable
from reportlab.platypus.tables import TableStyle, Table
from reportlab.platypus.flowables import Spacer
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
import unicodedata
from ast import literal_eval

def unquote(txt):
    from xml.sax.saxutils import unescape
    return unescape(txt, {"&apos;": "'", "&quot;": '"'})

try:
    set
except:
    class set(list):
        def add(self,x):
            if x not in self:
                list.append(self,x)

def drawPageNumbers(canvas, style, pages, availWidth, availHeight, dot=' . ', formatter=None):
    '''
    Draws pagestr on the canvas using the given style.
    If dot is None, pagestr is drawn at the current position in the canvas.
    If dot is a string, pagestr is drawn right-aligned. If the string is not empty,
    the gap is filled with it.
    '''
    pagestr = ', '.join([str(p) for p, _ in pages])
    x, y = canvas._curr_tx_info['cur_x'], canvas._curr_tx_info['cur_y']

    fontSize = style.fontSize
    pagestrw = stringWidth(pagestr, style.fontName, fontSize)

    #if it's too long to fit, we need to shrink to fit in 10% increments.
    #it would be very hard to output multiline entries.
    #however, we impose a minimum size of 1 point as we don't want an
    #infinite loop.   Ultimately we should allow a TOC entry to spill
    #over onto a second line if needed.
    freeWidth = availWidth-x
    while pagestrw > freeWidth and fontSize >= 1.0:
        fontSize = 0.9 * fontSize
        pagestrw = stringWidth(pagestr, style.fontName, fontSize)


    if isinstance(dot, strTypes):
        if dot:
            dotw = stringWidth(dot, style.fontName, fontSize)
            dotsn = int((availWidth-x-pagestrw)/dotw)
        else:
            dotsn = dotw = 0
        text = '%s%s' % (dotsn * dot, pagestr)
        newx = availWidth - dotsn*dotw - pagestrw
        pagex = availWidth - pagestrw
    elif dot is None:
        text = ',  ' + pagestr
        newx = x
        pagex = newx
    else:
        raise TypeError('Argument dot should either be None or an instance of basestring.')

    tx = canvas.beginText(newx, y)
    tx.setFont(style.fontName, fontSize)
    tx.setFillColor(style.textColor)
    tx.textLine(text)
    canvas.drawText(tx)

    commaw = stringWidth(', ', style.fontName, fontSize)
    for p, key in pages:
        if not key:
            continue
        w = stringWidth(str(p), style.fontName, fontSize)
        canvas.linkRect('', key, (pagex, y, pagex+w, y+style.leading), relative=1)
        pagex += w + commaw

# Default paragraph styles for tables of contents.
# (This could also be generated automatically or even
# on-demand if it is not known how many levels the
# TOC will finally need to display...)

delta = 1*cm
epsilon = 0.5*cm

defaultLevelStyles = [
    ParagraphStyle(
        name='Level 0',
        fontName=_baseFontName,
        fontSize=10,
        leading=11,
        firstLineIndent = 0,
        leftIndent = epsilon)]

defaultTableStyle = \
    TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ])

class TableOfContents(IndexingFlowable):
    """This creates a formatted table of contents.

    It presumes a correct block of data is passed in.
    The data block contains a list of (level, text, pageNumber)
    triplets.  You can supply a paragraph style for each level
    (starting at zero).
    Set dotsMinLevel to determine from which level on a line of
    dots should be drawn between the text and the page number.
    If dotsMinLevel is set to a negative value, no dotted lines are drawn.
    """

    def __init__(self,**kwds):
        self.rightColumnWidth = kwds.pop('rightColumnWidth',72)
        self.levelStyles = kwds.pop('levelStyles',defaultLevelStyles)
        self.tableStyle = kwds.pop('tableStyle',defaultTableStyle)
        self.dotsMinLevel = kwds.pop('dotsMinLevel',1)
        self.formatter = kwds.pop('formatter',None)
        self._notifyKind = kwds.pop('notifyKind','TOCEntry')
        if kwds: raise ValueError('unexpected keyword arguments %s' % ', '.join(kwds.keys()))
        self._table = None
        self._entries = []
        self._lastEntries = []

    def beforeBuild(self):
        # keep track of the last run
        self._lastEntries = self._entries[:]
        self.clearEntries()

    def isIndexing(self):
        return 1

    def isSatisfied(self):
        return (self._entries == self._lastEntries)

    def notify(self, kind, stuff):
        """The notification hook called to register all kinds of events.

        Here we are interested in self._notifyKind (default TOCEntry) events only.
        """
        if kind == self._notifyKind:
            self.addEntry(*stuff)

    def clearEntries(self):
        self._entries = []

    def getLevelStyle(self, n):
        '''Returns the style for level n, generating and caching styles on demand if not present.'''
        try:
            return self.levelStyles[n]
        except IndexError:
            prevstyle = self.getLevelStyle(n-1)
            self.levelStyles.append(ParagraphStyle(
                    name='%s-%d-indented' % (prevstyle.name, n),
                    parent=prevstyle,
                    firstLineIndent = prevstyle.firstLineIndent+delta,
                    leftIndent = prevstyle.leftIndent+delta))
            return self.levelStyles[n]

    def addEntry(self, level, text, pageNum, key=None):
        """Adds one entry to the table of contents.

        This allows incremental buildup by a doctemplate.
        Requires that enough styles are defined."""

        assert type(level) == type(1), "Level must be an integer"
        self._entries.append((level, text, pageNum, key))


    def addEntries(self, listOfEntries):
        """Bulk creation of entries in the table of contents.

        If you knew the titles but not the page numbers, you could
        supply them to get sensible output on the first run."""

        for entryargs in listOfEntries:
            self.addEntry(*entryargs)


    def wrap(self, availWidth, availHeight):
        "All table properties should be known by now."

        # makes an internal table which does all the work.
        # we draw the LAST RUN's entries!  If there are
        # none, we make some dummy data to keep the table
        # from complaining
        if len(self._lastEntries) == 0:
            _tempEntries = [(0,'Placeholder for table of contents',0,None)]
        else:
            _tempEntries = self._lastEntries

        def drawTOCEntryEnd(canvas, kind, label):
            '''Callback to draw dots and page numbers after each entry.'''
            label = label.split(',')
            page, level, key = int(label[0]), int(label[1]), literal_eval(label[2])
            style = self.getLevelStyle(level)
            if self.dotsMinLevel >= 0 and level >= self.dotsMinLevel:
                dot = ' . '
            else:
                dot = ''
            if self.formatter: page = self.formatter(page)
            drawPageNumbers(canvas, style, [(page, key)], availWidth, availHeight, dot)
        self.canv.drawTOCEntryEnd = drawTOCEntryEnd

        tableData = []
        for (level, text, pageNum, key) in _tempEntries:
            style = self.getLevelStyle(level)
            if key:
                text = '<a href="#%s">%s</a>' % (key, text)
                keyVal = repr(key).replace(',','\\x2c').replace('"','\\x2c')
            else:
                keyVal = None
            para = Paragraph('%s<onDraw name="drawTOCEntryEnd" label="%d,%d,%s"/>' % (text, pageNum, level, keyVal), style)
            if style.spaceBefore:
                tableData.append([Spacer(1, style.spaceBefore),])
            tableData.append([para,])

        self._table = Table(tableData, colWidths=(availWidth,), style=self.tableStyle)

        self.width, self.height = self._table.wrapOn(self.canv,availWidth, availHeight)
        return (self.width, self.height)


    def split(self, availWidth, availHeight):
        """At this stage we do not care about splitting the entries,
        we will just return a list of platypus tables.  Presumably the
        calling app has a pointer to the original TableOfContents object;
        Platypus just sees tables.
        """
        return self._table.splitOn(self.canv,availWidth, availHeight)


    def drawOn(self, canvas, x, y, _sW=0):
        """Don't do this at home!  The standard calls for implementing
        draw(); we are hooking this in order to delegate ALL the drawing
        work to the embedded table object.
        """
        self._table.drawOn(canvas, x, y, _sW)

def makeTuple(x):
    if isinstance(x,(list,tuple)):
        return tuple(x)
    return (x,)

class SimpleIndex(IndexingFlowable):
    """Creates multi level indexes.
    The styling can be cutomized and alphabetic headers turned on and off.
    """

    def __init__(self, **kwargs):
        """
        Constructor of SimpleIndex.
        Accepts the same arguments as the setup method.
        """
        #keep stuff in a dictionary while building
        self._entries = {}
        self._lastEntries = {}
        self._flowable = None
        self._notifyKind = kwargs.pop('notifyKind','IndexEntry')
        self.setup(**kwargs)

    def getFormatFunc(self,formatName):
        try:
            return getattr(rl_sequencer,'_format_%s' % formatName)
        except ImportError:
            raise ValueError('Unknown sequencer format %r' % formatName)

    def setup(self, style=None, dot=None, tableStyle=None, headers=True, name=None, format='123', offset=0):
        """
        This method makes it possible to change styling and other parameters on an existing object.

        style is the paragraph style to use for index entries.
        dot can either be None or a string. If it's None, entries are immediatly followed by their
            corresponding page numbers. If it's a string, page numbers are aligned on the right side
            of the document and the gap filled with a repeating sequence of the string.
        tableStyle is the style used by the table which the index uses to draw itself. Use this to
            change properties like spacing between elements.
        headers is a boolean. If it is True, alphabetic headers are displayed in the Index when the first
        letter changes. If False, we just output some extra space before the next item
        name makes it possible to use several indexes in one document. If you want this use this
            parameter to give each index a unique name. You can then index a term by refering to the
            name of the index which it should appear in:

                <index item="term" name="myindex" />

        format can be 'I', 'i', '123',  'ABC', 'abc'
        """

        if style is None:
            style = ParagraphStyle(name='index',
                                        fontName=_baseFontName,
                                        fontSize=11)
        self.textStyle = style
        self.tableStyle = tableStyle or defaultTableStyle
        self.dot = dot
        self.headers = headers
        if name is None:
            from reportlab.platypus.paraparser import DEFAULT_INDEX_NAME as name
        self.name = name
        self.formatFunc = self.getFormatFunc(format)
        self.offset = offset

    def __call__(self,canv,kind,label):
        label = asNative(label,'latin1')
        try:
            terms, format, offset = decode_label(label)
        except:
            terms = label
            format = offset = None
        if format is None:
            formatFunc = self.formatFunc
        else:
            formatFunc = self.getFormatFunc(format)
        if offset is None:
            offset = self.offset

        terms = commasplit(terms)
        cPN = canv.getPageNumber()
        pns = formatFunc(cPN-offset)
        key = 'ix_%s_%s_p_%s' % (self.name, label, pns)

        info = canv._curr_tx_info
        canv.bookmarkHorizontal(key, info['cur_x'], info['cur_y'] + info['leading'])
        self.addEntry(terms, (cPN,pns), key)

    def getCanvasMaker(self, canvasmaker=canvas.Canvas):

        def newcanvasmaker(*args, **kwargs):
            from reportlab.pdfgen import canvas
            c = canvasmaker(*args, **kwargs)
            setattr(c,self.name,self)
            return c

        return newcanvasmaker

    def isIndexing(self):
        return 1

    def isSatisfied(self):
        return (self._entries == self._lastEntries)

    def beforeBuild(self):
        # keep track of the last run
        self._lastEntries = self._entries.copy()
        self.clearEntries()

    def clearEntries(self):
        self._entries = {}

    def notify(self, kind, stuff):
        """The notification hook called to register all kinds of events.

        Here we are interested in self._notifyKind (default IndexEntry) events only.
        """
        if kind == self._notifyKind:
            text, pageNum = stuff
            self.addEntry(text, (self._canv.getPageNumber(),pageNum))

    def addEntry(self, text, pageNum, key=None):
        """Allows incremental buildup"""
        self._entries.setdefault(makeTuple(text),set([])).add((pageNum, key))

    def split(self, availWidth, availHeight):
        """At this stage we do not care about splitting the entries,
        we will just return a list of platypus tables.  Presumably the
        calling app has a pointer to the original TableOfContents object;
        Platypus just sees tables.
        """
        return self._flowable.splitOn(self.canv,availWidth, availHeight)

    def _getlastEntries(self, dummy=[(['Placeholder for index'],enumerate((None,)*3))]):
        '''Return the last run's entries!  If there are none, returns dummy.'''
        lE = self._lastEntries or self._entries
        if not lE:
            return dummy
        return list(sorted(lE.items()))

    def _build(self,availWidth,availHeight):
        _tempEntries = [(tuple(asUnicode(t) for t in texts),pageNumbers)
                            for texts, pageNumbers in self._getlastEntries()]
        def getkey(seq):
            return [''.join((c for c in unicodedata.normalize('NFD', x.upper()) if unicodedata.category(c) != 'Mn')) for x in seq[0]]
        _tempEntries.sort(key=getkey)
        leveloffset = self.headers and 1 or 0

        def drawIndexEntryEnd(canvas, kind, label):
            '''Callback to draw dots and page numbers after each entry.'''
            style = self.getLevelStyle(leveloffset)
            pages = [(p[1],k) for p,k in sorted(decode_label(label))]
            drawPageNumbers(canvas, style, pages, availWidth, availHeight, self.dot)
        self.canv.drawIndexEntryEnd = drawIndexEntryEnd

        alpha = ''
        tableData = []
        lastTexts = []
        alphaStyle = self.getLevelStyle(0)
        for texts, pageNumbers in _tempEntries:
            texts = list(texts)
            #track when the first character changes; either output some extra
            #space, or the first letter on a row of its own.  We cannot do
            #widow/orphan control, sadly.
            nalpha = ''.join((c for c in unicodedata.normalize('NFD', texts[0][0].upper()) if unicodedata.category(c) != 'Mn'))
            if alpha != nalpha:
                alpha = nalpha
                if self.headers:
                    header = alpha
                else:
                    header = ' '
                tableData.append([Spacer(1, alphaStyle.spaceBefore),])
                tableData.append([Paragraph(header, alphaStyle),])
                tableData.append([Spacer(1, alphaStyle.spaceAfter),])


            i, diff = listdiff(lastTexts, texts)
            if diff:
                lastTexts = texts
                texts = texts[i:]
            label = encode_label(list(pageNumbers))
            texts[-1] = '%s<onDraw name="drawIndexEntryEnd" label="%s"/>' % (texts[-1], label)
            for text in texts:
                #Platypus and RML differ on how parsed XML attributes are escaped.
                #e.g. <index item="M&S"/>.  The only place this seems to bite us is in
                #the index entries so work around it here.
                text = escapeOnce(text)

                style = self.getLevelStyle(i+leveloffset)
                para = Paragraph(text, style)
                if style.spaceBefore:
                    tableData.append([Spacer(1, style.spaceBefore),])
                tableData.append([para,])
                i += 1

        self._flowable = Table(tableData, colWidths=[availWidth], style=self.tableStyle)

    def wrap(self, availWidth, availHeight):
        "All table properties should be known by now."
        self._build(availWidth,availHeight)
        self.width, self.height = self._flowable.wrapOn(self.canv,availWidth, availHeight)
        return self.width, self.height

    def drawOn(self, canvas, x, y, _sW=0):
        """Don't do this at home!  The standard calls for implementing
        draw(); we are hooking this in order to delegate ALL the drawing
        work to the embedded table object.
        """
        self._flowable.drawOn(canvas, x, y, _sW)

    def draw(self):
        t = self._flowable
        ocanv = getattr(t,'canv',None)
        if not ocanv:
            t.canv = self.canv
        try:
            t.draw()
        finally:
            if not ocanv:
                del t.canv

    def getLevelStyle(self, n):
        '''Returns the style for level n, generating and caching styles on demand if not present.'''
        if not hasattr(self.textStyle, '__iter__'):
            self.textStyle = [self.textStyle]
        try:
            return self.textStyle[n]
        except IndexError:
            self.textStyle = list(self.textStyle)
            prevstyle = self.getLevelStyle(n-1)
            self.textStyle.append(ParagraphStyle(
                    name='%s-%d-indented' % (prevstyle.name, n),
                    parent=prevstyle,
                    firstLineIndent = prevstyle.firstLineIndent+.2*cm,
                    leftIndent = prevstyle.leftIndent+.2*cm))
            return self.textStyle[n]

AlphabeticIndex =  SimpleIndex

def listdiff(l1, l2):
    m = min(len(l1), len(l2))
    for i in range(m):
        if l1[i] != l2[i]:
            return i, l2[i:]
    return m, l2[m:]

class ReferenceText(IndexingFlowable):
    """Fakery to illustrate how a reference would work if we could
    put it in a paragraph."""
    def __init__(self, textPattern, targetKey):
        self.textPattern = textPattern
        self.target = targetKey
        self.paraStyle = ParagraphStyle('tmp')
        self._lastPageNum = None
        self._pageNum = -999
        self._para = None

    def beforeBuild(self):
        self._lastPageNum = self._pageNum

    def notify(self, kind, stuff):
        if kind == 'Target':
            (key, pageNum) = stuff
            if key == self.target:
                self._pageNum = pageNum

    def wrap(self, availWidth, availHeight):
        text = self.textPattern % self._lastPageNum
        self._para = Paragraph(text, self.paraStyle)
        return self._para.wrap(availWidth, availHeight)

    def drawOn(self, canvas, x, y, _sW=0):
        self._para.drawOn(canvas, x, y, _sW)
