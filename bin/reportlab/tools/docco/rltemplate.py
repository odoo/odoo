#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/rltemplate.py
# doc template for RL manuals.  Currently YAML is hard-coded
#to use this, which is wrong.


from reportlab.platypus import PageTemplate, \
     BaseDocTemplate, Frame, Paragraph
from reportlab.lib.units import inch, cm
from reportlab.rl_config import defaultPageSize


class FrontCoverTemplate(PageTemplate):
    def __init__(self, id, pageSize=defaultPageSize):
        self.pageWidth = pageSize[0]
        self.pageHeight = pageSize[1]
        frame1 = Frame(inch,
                       3*inch,
                       self.pageWidth - 2*inch,
                       self.pageHeight - 518, id='cover')
        PageTemplate.__init__(self, id, [frame1])  # note lack of onPage

    def afterDrawPage(self, canvas, doc):
        canvas.saveState()
        canvas.drawImage('../images/replogo.gif',2*inch, 8*inch)


        canvas.setFont('Times-Roman', 10)
        canvas.line(inch, 120, self.pageWidth - inch, 120)

        canvas.drawString(inch, 100, '165 The Broadway')
        canvas.drawString(inch, 88, 'Wimbledon')
        canvas.drawString(inch, 76, 'London SW19 1NE')
        canvas.drawString(inch, 64, 'United Kingdom')

        canvas.restoreState()


class OneColumnTemplate(PageTemplate):
    def __init__(self, id, pageSize=defaultPageSize):
        self.pageWidth = pageSize[0]
        self.pageHeight = pageSize[1]
        frame1 = Frame(inch,
                       inch,
                       self.pageWidth - 2*inch,
                       self.pageHeight - 2*inch,
                       id='normal')
        PageTemplate.__init__(self, id, [frame1])  # note lack of onPage

    def afterDrawPage(self, canvas, doc):
        y = self.pageHeight - 50
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(inch, y+8, doc.title)
        canvas.drawRightString(self.pageWidth - inch, y+8, doc.chapter)
        canvas.line(inch, y, self.pageWidth - inch, y)
        canvas.drawCentredString(doc.pagesize[0] / 2, 0.75*inch, 'Page %d' % canvas.getPageNumber())
        canvas.restoreState()

class TwoColumnTemplate(PageTemplate):
    def __init__(self, id, pageSize=defaultPageSize):
        self.pageWidth = pageSize[0]
        self.pageHeight = pageSize[1]
        colWidth = 0.5 * (self.pageWidth - 2.25*inch)
        frame1 = Frame(inch,
                       inch,
                       colWidth,
                       self.pageHeight - 2*inch,
                       id='leftCol')
        frame2 = Frame(0.5 * self.pageWidth + 0.125,
                       inch,
                       colWidth,
                       self.pageHeight - 2*inch,
                       id='rightCol')
        PageTemplate.__init__(self, id, [frame1, frame2])  # note lack of onPage

    def afterDrawPage(self, canvas, doc):
        y = self.pageHeight - 50
        canvas.saveState()
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(inch, y+8, doc.title)
        canvas.drawRightString(self.pageWidth - inch, y+8, doc.chapter)
        canvas.line(inch, y, self.pageWidth - inch, y*inch)
        canvas.drawCentredString(doc.pagesize[0] / 2, 0.75*inch, 'Page %d' % canvas.getPageNumber())
        canvas.restoreState()


class RLDocTemplate(BaseDocTemplate):
    def afterInit(self):
        self.addPageTemplates(FrontCoverTemplate('Cover', self.pagesize))
        self.addPageTemplates(OneColumnTemplate('Normal', self.pagesize))
        self.addPageTemplates(TwoColumnTemplate('TwoColumn', self.pagesize))

        #just playing
        self.title = "(Document Title Goes Here)"
        self.chapter = "(No chapter yet)"
        self.chapterNo = 1 #unique keys
        self.sectionNo = 1 # unique keys

##        # AR hack
##        self.counter = 1
    def beforeDocument(self):
        self.canv.showOutline()

    def afterFlowable(self, flowable):
        """Detect Level 1 and 2 headings, build outline,
        and track chapter title."""
        if isinstance(flowable, Paragraph):
            style = flowable.style.name

##            #AR debug text
##            try:
##                print '%d: %s...' % (self.counter, flowable.getPlainText()[0:40])
##            except AttributeError:
##                print '%d: (something with ABag)' % self.counter
##            self.counter = self.counter + 1

            if style == 'Title':
                self.title = flowable.getPlainText()
            elif style == 'Heading1':
                self.chapter = flowable.getPlainText()
                key = 'ch%d' % self.chapterNo
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.getPlainText(),
                                            key, 0, 0)
                self.chapterNo = self.chapterNo + 1
                self.sectionNo = 1
            elif style == 'Heading2':
                self.section = flowable.text
                key = 'ch%ds%d' % (self.chapterNo, self.sectionNo)
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.getPlainText(),
                                             key, 1, 0)
                self.sectionNo = self.sectionNo + 1