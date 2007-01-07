# Tables of Contents and Indices
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/lib/tocindex.py
__version__=''' $Id: tocindex.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
__doc__=''
"""
This module will contain standard Table of Contents and Index objects.
under development, and pending certain hooks adding in DocTemplate
As of today, it onyl handles the formatting aspect of TOCs
"""

import string

from reportlab.platypus import Flowable, BaseDocTemplate, Paragraph, \
     PageBreak, Frame, PageTemplate, NextPageTemplate
from reportlab.platypus.doctemplate import IndexingFlowable
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import tables
from reportlab.lib import enums
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.rl_config import defaultPageSize

    ##############################################################
    #
    # we first define a paragraph style for each level of the
    # table, and one for the table as whole; you can supply your
    # own.
    #
    ##############################################################


levelZeroParaStyle = ParagraphStyle(name='LevelZero',
                                  fontName='Times-Roman',
                                  fontSize=10,
                                  leading=12)
levelOneParaStyle = ParagraphStyle(name='LevelOne',
                                   parent = levelZeroParaStyle,
                                   firstLineIndent = 0,
                                   leftIndent = 18)
levelTwoParaStyle = ParagraphStyle(name='LevelTwo',
                                   parent = levelOneParaStyle,
                                   firstLineIndent = 0,
                                   leftIndent = 36)
levelThreeParaStyle = ParagraphStyle(name='LevelThree',
                                   parent = levelTwoParaStyle,
                                   firstLineIndent = 0,
                                   leftIndent = 54)

defaultTableStyle = tables.TableStyle([
                        ('VALIGN',(0,0),(-1,-1),'TOP'),
                        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ])






class TableOfContents0(IndexingFlowable):
    """This creates a formatted table of contents.  It presumes
    a correct block of data is passed in.  The data block contains
    a list of (level, text, pageNumber) triplets.  You can supply
    a paragraph style for each level (starting at zero)."""
    def __init__(self):
        self.entries = []
        self.rightColumnWidth = 72
        self.levelStyles = [levelZeroParaStyle,
                            levelOneParaStyle,
                            levelTwoParaStyle,
                            levelThreeParaStyle]
        self.tableStyle = defaultTableStyle
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
        """DocTemplate framework can call this with all kinds
        of events; we say we are interested in 'TOCEntry'
        events."""
        if kind == 'TOCEntry':
            (level, text, pageNum) = stuff
            self.addEntry(level, text, pageNum)
            #print 'TOC notified of ', stuff
##        elif kind == 'debug':
##            # hack to watch its state
##            import pprint
##            print 'Last Entries first 5:'
##            for (level, text, pageNum) in self._lastEntries[0:5]:
##                print (level, text[0:30], pageNum),
##            print
##            print 'Current Entries first 5:'
##            for (level, text, pageNum) in self._lastEntries[0:5]:
##                print (level, text[0:30], pageNum),


    def clearEntries(self):
        self._entries = []

    def addEntry(self, level, text, pageNum):
        """Adds one entry; allows incremental buildup by a doctemplate.
        Requires that enough styles are defined."""
        assert type(level) == type(1), "Level must be an integer"
        assert level < len(self.levelStyles), \
               "Table of contents must have a style defined " \
               "for paragraph level %d before you add an entry" % level
        self._entries.append((level, text, pageNum))

    def addEntries(self, listOfEntries):
        """Bulk creation.  If you knew the titles but
        not the page numbers, you could supply them to
        get sensible output on the first run."""
        for (level, text, pageNum) in listOfEntries:
            self.addEntry(level, text, pageNum)

    def wrap(self, availWidth, availHeight):
        """All table properties should be known by now."""
        widths = (availWidth - self.rightColumnWidth,
                  self.rightColumnWidth)

        # makes an internal table which does all the work.
        # we draw the LAST RUN's entries!  If there are
        # none, we make some dummy data to keep the table
        # from complaining
        if len(self._lastEntries) == 0:
            _tempEntries = [(0,'Placeholder for table of contents',0)]
        else:
            _tempEntries = self._lastEntries
        tableData = []
        for (level, text, pageNum) in _tempEntries:
            leftColStyle = self.levelStyles[level]
            #right col style is right aligned
            rightColStyle = ParagraphStyle(name='leftColLevel%d' % level,
                                           parent=leftColStyle,
                                           leftIndent=0,
                                           alignment=enums.TA_RIGHT)
            leftPara = Paragraph(text, leftColStyle)
            rightPara = Paragraph(str(pageNum), rightColStyle)
            tableData.append([leftPara, rightPara])
        self._table = tables.Table(tableData, colWidths=widths,
                                   style=self.tableStyle)
        self.width, self.height = self._table.wrap(availWidth, availHeight)
        return (self.width, self.height)

    def split(self, availWidth, availHeight):
        """At this stage we do not care about splitting the entries,
        we wil just return a list of platypus tables.  Presumably the
        calling app has a pointer to the original TableOfContents object;
        Platypus just sees tables."""
        return self._table.split(availWidth, availHeight)

    def drawOn(self, canvas, x, y, _sW=0):
        """Don't do this at home!  The standard calls for implementing
        draw(); we are hooking this in order to delegate ALL the drawing
        work to the embedded table object"""
        self._table.drawOn(canvas, x, y, _sW)



    #################################################################################
    #
    # everything from here down is concerned with creating a good example document
    # i.e. test code as well as tutorial
PAGE_HEIGHT = defaultPageSize[1]
def getSampleTOCData(depth=3):
    """Returns a longish block of page numbers and headings over 3 levels"""
    from random import randint
    pgNum = 2
    data = []
    for chapter in range(1,8):
        data.append((0, """Chapter %d with a really long name which will hopefully
        wrap onto a second line, fnding out if the right things happen with
        full paragraphs n the table of contents""" % chapter, pgNum))
        pgNum = pgNum + randint(0,2)
        if depth > 1:
            for section in range(1,5):
                data.append((1, 'Chapter %d Section %d' % (chapter, section), pgNum))
                pgNum = pgNum + randint(0,2)
                if depth > 2:
                    for subSection in range(1,6):
                        data.append(2, 'Chapter %d Section %d Subsection %d' %
                                    (chapter, section, subSection),
                                    pgNum)
                        pgNum = pgNum + randint(0,1)
    from pprint import pprint as pp
    pp(data)
    return data


def getSampleStory(depth=3):
    """Makes a story with lots of paragraphs.  Uses the random
    TOC data and makes paragraphs to correspond to each."""
    from reportlab.platypus.doctemplate import randomText
    from random import randint

    styles = getSampleStyleSheet()
    TOCData = getSampleTOCData(depth)

    story = [Paragraph("This is a demo of the table of contents object",
                       styles['Heading1'])]

    toc = TableOfContents0()  # empty on first pass
    #toc.addEntries(TOCData)  # init with random page numbers
    story.append(toc)

    # the next full page should switch to internal page style
    story.append(NextPageTemplate("Body"))

    # now make some paragraphs to correspond to it
    for (level, text, pageNum) in TOCData:
        if level == 0:
            #page break before chapter
            story.append(PageBreak())

        headingStyle = (styles['Heading1'], styles['Heading2'], styles['Heading3'])[level]
        headingPara = Paragraph(text, headingStyle)
        story.append(headingPara)
        # now make some body text
        for i in range(randint(1,6)):
            bodyPara = Paragraph(randomText(),
                                 styles['Normal'])
            story.append(bodyPara)

    return story

class MyDocTemplate(BaseDocTemplate):
    """Example of how to do the indexing.  Need the onDraw hook
    to find out which things are drawn on which pages"""
    def afterInit(self):
        """Set up the page templates"""
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='Front',frames=frameT),
                          PageTemplate(id='Body',frames=frameT)
                          ])
        # just need a unique key generator for outline entries;
        # easiest is to count all flowables in afterFlowable
        # and set up a counter variable here
        self._uniqueKey = 0


    def afterFlowable(self, flowable):
        """Our rule for the table of contents is simply to take
        the text of H1, H2 and H3 elements. We broadcast a
        notification to the DocTemplate, which should inform
        the TOC and let it pull them out. Also build an outline"""
        self._uniqueKey = self._uniqueKey + 1

        if hasattr(flowable, 'style'):
            if flowable.style.name == 'Heading1':
                self.notify('TOCEntry', (0, flowable.getPlainText(), self.page))
                self.canv.bookmarkPage(str(self._uniqueKey))
                self.canv.addOutlineEntry(flowable.getPlainText()[0:10], str(self._uniqueKey), 0)

            elif flowable.style.name == 'Heading2':
                self.notify('TOCEntry', (1, flowable.getPlainText(), self.page))
                self.canv.bookmarkPage(str(self._uniqueKey))
                self.canv.addOutlineEntry(flowable.getPlainText(), str(self._uniqueKey), 1)

            elif flowable.style.name == 'Heading3':
                self.notify('TOCEntry', (2, flowable.getPlainText(), self.page))
                self.canv.bookmarkPage(str(self._uniqueKey))
                self.canv.addOutlineEntry(flowable.getPlainText(), str(self._uniqueKey), 2)

    def beforePage(self):
        """decorate the page"""
        self.canv.saveState()
        self.canv.setStrokeColor(colors.red)
        self.canv.setLineWidth(5)
        self.canv.line(66,72,66,PAGE_HEIGHT-72)
        self.canv.setFont('Times-Roman',12)
        self.canv.drawString(4 * inch, 0.75 * inch, "Page %d" % doc.page)
        self.canv.restoreState()

if __name__=='__main__':
    from reportlab.platypus import SimpleDocTemplate
    doc = MyDocTemplate('tocindex.pdf')

    #change this to depth=3 for a BIG document
    story = getSampleStory(depth=2)

    doc.multiBuild(story, 'tocindex.pdf')