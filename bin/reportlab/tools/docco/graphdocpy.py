#!/usr/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/graphdocpy.py

"""Generate documentation for reportlab.graphics classes.

Type the following for usage info:

  python graphdocpy.py -h
"""


__version__ = '0.8'


import sys
sys.path.insert(0, '.')
import os, re, types, string, getopt, pickle, copy, time, pprint, traceback
from string import find, join, split, replace, expandtabs, rstrip
import reportlab
from reportlab import rl_config

from docpy import PackageSkeleton0, ModuleSkeleton0
from docpy import DocBuilder0, PdfDocBuilder0, HtmlDocBuilder0
from docpy import htmlescape, htmlrepr, defaultformat, \
     getdoc, reduceDocStringLength
from docpy import makeHtmlSection, makeHtmlSubSection, \
     makeHtmlInlineImage

from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import getStringIO
#from StringIO import StringIO
#getStringIO=StringIO
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable, Spacer
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.flowables \
     import Flowable, Preformatted,Spacer, Image, KeepTogether, PageBreak
from reportlab.platypus.xpreformatted import XPreformatted
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate \
     import PageTemplate, BaseDocTemplate
from reportlab.platypus.tables import TableStyle, Table
from reportlab.graphics.shapes import NotImplementedError
import inspect

# Needed to draw Widget/Drawing demos.

from reportlab.graphics.widgetbase import Widget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import shapes
from reportlab.graphics import renderPDF

VERBOSE = rl_config.verbose
VERIFY = 1

_abstractclasserr_re = re.compile(r'^\s*abstract\s*class\s*(\w+)\s*instantiated',re.I)

####################################################################
#
# Stuff needed for building PDF docs.
#
####################################################################

def mainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()

    pageNumber = canvas.getPageNumber()
    canvas.line(2*cm, A4[1]-2*cm, A4[0]-2*cm, A4[1]-2*cm)
    canvas.line(2*cm, 2*cm, A4[0]-2*cm, 2*cm)
    if pageNumber > 1:
        canvas.setFont('Times-Roman', 12)
        canvas.drawString(4 * inch, cm, "%d" % pageNumber)
        if hasattr(canvas, 'headerLine'): # hackish
            headerline = string.join(canvas.headerLine, ' \xc2\x8d ')
            canvas.drawString(2*cm, A4[1]-1.75*cm, headerline)

    canvas.setFont('Times-Roman', 8)
    msg = "Generated with docpy. See http://www.reportlab.com!"
    canvas.drawString(2*cm, 1.65*cm, msg)

    canvas.restoreState()


class MyTemplate(BaseDocTemplate):
    "The document template used for all PDF documents."

    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        frame1 = Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')
        self.allowSplitting = 0
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        self.addPageTemplates(PageTemplate('normal', [frame1], mainPageFrame))

    def afterFlowable(self, flowable):
        "Takes care of header line, TOC and outline entries."

        if flowable.__class__.__name__ == 'Paragraph':
            f = flowable

            # Build a list of heading parts.
            # So far, this is the *last* item on the *previous* page...
            if f.style.name[:8] == 'Heading0':
                self.canv.headerLine = [f.text] # hackish
            elif f.style.name[:8] == 'Heading1':
                if len(self.canv.headerLine) == 2:
                    del self.canv.headerLine[-1]
                elif len(self.canv.headerLine) == 3:
                    del self.canv.headerLine[-1]
                    del self.canv.headerLine[-1]
                self.canv.headerLine.append(f.text)
            elif f.style.name[:8] == 'Heading2':
                if len(self.canv.headerLine) == 3:
                    del self.canv.headerLine[-1]
                self.canv.headerLine.append(f.text)

            if f.style.name[:7] == 'Heading':
                # Register TOC entries.
                headLevel = int(f.style.name[7:])
                self.notify('TOCEntry', (headLevel, flowable.getPlainText(), self.page))

                # Add PDF outline entries.
                c = self.canv
                title = f.text
                key = str(hash(f))
                lev = int(f.style.name[7:])
                try:
                    if lev == 0:
                        isClosed = 0
                    else:
                        isClosed = 1
                    c.bookmarkPage(key)
                    c.addOutlineEntry(title, key, level=lev, closed=isClosed)
                    c.showOutline()
                except:
                    if VERBOSE:
                        # AR hacking in exception handlers
                        print 'caught exception in MyTemplate.afterFlowable with heading text %s' % f.text
                        traceback.print_exc()
                    else:
                        pass


####################################################################
#
# Utility functions
#
####################################################################
def indentLevel(line, spacesPerTab=4):
    """Counts the indent levels on the front.

    It is assumed that one tab equals 4 spaces.
    """

    x = 0
    nextTab = 4
    for ch in line:
        if ch == ' ':
            x = x + 1
        elif ch == '\t':
            x = nextTab
            nextTab = x + spacesPerTab
        else:
            return x


assert indentLevel('hello') == 0, 'error in indentLevel'
assert indentLevel(' hello') == 1, 'error in indentLevel'
assert indentLevel('  hello') == 2, 'error in indentLevel'
assert indentLevel('   hello') == 3, 'error in indentLevel'
assert indentLevel('\thello') == 4, 'error in indentLevel'
assert indentLevel(' \thello') == 4, 'error in indentLevel'
assert indentLevel('\t hello') == 5, 'error in indentLevel'

####################################################################
#
# Special-purpose document builders
#
####################################################################

class GraphPdfDocBuilder0(PdfDocBuilder0):
    """A PDF document builder displaying widgets and drawings.

    This generates a PDF file where only methods named 'demo' are
    listed for any class C. If C happens to be a subclass of Widget
    and has a 'demo' method, this method is assumed to generate and
    return a sample widget instance, that is then appended graphi-
    cally to the Platypus story.

    Something similar happens for functions. If their names start
    with 'sample' they are supposed to generate and return a sample
    drawing. This is then taken and appended graphically to the
    Platypus story, as well.
    """

    fileSuffix = '.pdf'

    def begin(self, name='', typ=''):
        styleSheet = getSampleStyleSheet()
        self.code = styleSheet['Code']
        self.bt = styleSheet['BodyText']
        self.story = []

        # Cover page
        t = time.gmtime(time.time())
        timeString = time.strftime("%Y-%m-%d %H:%M", t)
        self.story.append(Paragraph('<font size=18>Documentation for %s "%s"</font>' % (typ, name), self.bt))
        self.story.append(Paragraph('<font size=18>Generated by: graphdocpy.py version %s</font>' %  __version__, self.bt))
        self.story.append(Paragraph('<font size=18>Date generated: %s</font>' % timeString, self.bt))
        self.story.append(Paragraph('<font size=18>Format: PDF</font>', self.bt))
        self.story.append(PageBreak())

        # Table of contents
        toc = TableOfContents()
        self.story.append(toc)
        self.story.append(PageBreak())


    def end(self, fileName=None):
        if fileName:  # overrides output path
            self.outPath = fileName
        elif self.packageName:
            self.outPath = self.packageName + self.fileSuffix
        elif self.skeleton:
            self.outPath = self.skeleton.getModuleName() + self.fileSuffix
        else:
            self.outPath = ''

        if self.outPath:
            doc = MyTemplate(self.outPath)
            doc.multiBuild(self.story)


    def beginModule(self, name, doc, imported):
        story = self.story
        bt = self.bt

        # Defer displaying the module header info to later...
        self.shouldDisplayModule = (name, doc, imported)
        self.hasDisplayedModule = 0


    def endModule(self, name, doc, imported):
        if self.hasDisplayedModule:
            DocBuilder0.endModule(self, name, doc, imported)


    def beginClasses(self, names):
        # Defer displaying the module header info to later...
        if self.shouldDisplayModule:
            self.shouldDisplayClasses = names


    # Skip all methods.
    def beginMethod(self, name, doc, sig):
        pass


    def endMethod(self, name, doc, sig):
        pass


    def beginClass(self, name, doc, bases):
        "Append a graphic demo of a Widget or Drawing at the end of a class."

        if VERBOSE:
            print 'GraphPdfDocBuilder.beginClass(%s...)' % name

        aClass = eval('self.skeleton.moduleSpace.' + name)
        if issubclass(aClass, Widget):
            if self.shouldDisplayModule:
                modName, modDoc, imported = self.shouldDisplayModule
                self.story.append(Paragraph(modName, self.makeHeadingStyle(self.indentLevel-2, 'module')))
                self.story.append(XPreformatted(modDoc, self.bt))
                self.shouldDisplayModule = 0
                self.hasDisplayedModule = 1
                if self.shouldDisplayClasses:
                    self.story.append(Paragraph('Classes', self.makeHeadingStyle(self.indentLevel-1)))
                    self.shouldDisplayClasses = 0
            PdfDocBuilder0.beginClass(self, name, doc, bases)
            self.beginAttributes(aClass)

        elif issubclass(aClass, Drawing):
            if self.shouldDisplayModule:
                modName, modDoc, imported = self.shouldDisplayModule
                self.story.append(Paragraph(modName, self.makeHeadingStyle(self.indentLevel-2, 'module')))
                self.story.append(XPreformatted(modDoc, self.bt))
                self.shouldDisplayModule = 0
                self.hasDisplayedModule = 1
                if self.shouldDisplayClasses:
                    self.story.append(Paragraph('Classes', self.makeHeadingStyle(self.indentLevel-1)))
                    self.shouldDisplayClasses = 0
            PdfDocBuilder0.beginClass(self, name, doc, bases)


    def beginAttributes(self, aClass):
        "Append a list of annotated attributes of a class."

        self.story.append(Paragraph(
            'Public Attributes',
            self.makeHeadingStyle(self.indentLevel+1)))

        map = aClass._attrMap
        if map:
            map = map.items()
            map.sort()
        else:
            map = []
        for name, typ in map:
            if typ != None:
                if hasattr(typ, 'desc'):
                    desc = typ.desc
                else:
                    desc = '<i>%s</i>' % typ.__class__.__name__
            else:
                desc = '<i>None</i>'
            self.story.append(Paragraph(
                "<b>%s</b> %s" % (name, desc), self.bt))
        self.story.append(Paragraph("", self.bt))


    def endClass(self, name, doc, bases):
        "Append a graphic demo of a Widget or Drawing at the end of a class."

        PdfDocBuilder0.endClass(self, name, doc, bases)

        aClass = eval('self.skeleton.moduleSpace.' + name)
        if hasattr(aClass, '_nodoc'):
            pass
        elif issubclass(aClass, Widget):
            try:
                widget = aClass()
            except AssertionError, err:
                if _abstractclasserr_re.match(str(err)): return
                raise
            self.story.append(Spacer(0*cm, 0.5*cm))
            self._showWidgetDemoCode(widget)
            self.story.append(Spacer(0*cm, 0.5*cm))
            self._showWidgetDemo(widget)
            self.story.append(Spacer(0*cm, 0.5*cm))
            self._showWidgetProperties(widget)
            self.story.append(PageBreak())
        elif issubclass(aClass, Drawing):
            drawing = aClass()
            self.story.append(Spacer(0*cm, 0.5*cm))
            self._showDrawingCode(drawing)
            self.story.append(Spacer(0*cm, 0.5*cm))
            self._showDrawingDemo(drawing)
            self.story.append(Spacer(0*cm, 0.5*cm))


    def beginFunctions(self, names):
        srch = string.join(names, ' ')
        if string.find(string.join(names, ' '), ' sample') > -1:
            PdfDocBuilder0.beginFunctions(self, names)


    # Skip non-sample functions.
    def beginFunction(self, name, doc, sig):
        "Skip function for 'uninteresting' names."

        if name[:6] == 'sample':
            PdfDocBuilder0.beginFunction(self, name, doc, sig)


    def endFunction(self, name, doc, sig):
        "Append a drawing to the story for special function names."

        if name[:6] != 'sample':
            return

        if VERBOSE:
            print 'GraphPdfDocBuilder.endFunction(%s...)' % name
        PdfDocBuilder0.endFunction(self, name, doc, sig)
        aFunc = eval('self.skeleton.moduleSpace.' + name)
        drawing = aFunc()

        self.story.append(Spacer(0*cm, 0.5*cm))
        self._showFunctionDemoCode(aFunc)
        self.story.append(Spacer(0*cm, 0.5*cm))
        self._showDrawingDemo(drawing)

        self.story.append(PageBreak())


    def _showFunctionDemoCode(self, function):
        """Show a demo code of the function generating the drawing."""
        # Heading
        self.story.append(Paragraph("<i>Example</i>", self.bt))
        self.story.append(Paragraph("", self.bt))

        # Sample code
        codeSample = inspect.getsource(function)
        self.story.append(Preformatted(codeSample, self.code))


    def _showDrawingCode(self, drawing):
        """Show code of the drawing class."""
        # Heading
        #className = drawing.__class__.__name__
        self.story.append(Paragraph("<i>Example</i>", self.bt))

        # Sample code
        codeSample = inspect.getsource(drawing.__class__.__init__)
        self.story.append(Preformatted(codeSample, self.code))


    def _showDrawingDemo(self, drawing):
        """Show a graphical demo of the drawing."""

        # Add the given drawing to the story.
        # Ignored if no GD rendering available
        # or the demo method does not return a drawing.
        try:
            flo = renderPDF.GraphicsFlowable(drawing)
            self.story.append(Spacer(6,6))
            self.story.append(flo)
            self.story.append(Spacer(6,6))
        except:
            if VERBOSE:
                print 'caught exception in _showDrawingDemo'
                traceback.print_exc()
            else:
                pass


    def _showWidgetDemo(self, widget):
        """Show a graphical demo of the widget."""

        # Get a demo drawing from the widget and add it to the story.
        # Ignored if no GD rendering available
        # or the demo method does not return a drawing.
        try:
            if VERIFY:
                widget.verify()
            drawing = widget.demo()
            flo = renderPDF.GraphicsFlowable(drawing)
            self.story.append(Spacer(6,6))
            self.story.append(flo)
            self.story.append(Spacer(6,6))
        except:
            if VERBOSE:
                print 'caught exception in _showWidgetDemo'
                traceback.print_exc()
            else:
                pass


    def _showWidgetDemoCode(self, widget):
        """Show a demo code of the widget."""
        # Heading
        #className = widget.__class__.__name__
        self.story.append(Paragraph("<i>Example</i>", self.bt))

        # Sample code
        codeSample = inspect.getsource(widget.__class__.demo)
        self.story.append(Preformatted(codeSample, self.code))


    def _showWidgetProperties(self, widget):
        """Dump all properties of a widget."""

        props = widget.getProperties()
        keys = props.keys()
        keys.sort()
        lines = []
        for key in keys:
            value = props[key]

            f = getStringIO()
            pprint.pprint(value, f)
            value = f.getvalue()[:-1]
            valueLines = string.split(value, '\n')
            for i in range(1, len(valueLines)):
                valueLines[i] = ' '*(len(key)+3) + valueLines[i]
            value = string.join(valueLines, '\n')

            lines.append('%s = %s' % (key, value))

        text = join(lines, '\n')
        self.story.append(Paragraph("<i>Properties of Example Widget</i>", self.bt))
        self.story.append(Paragraph("", self.bt))
        self.story.append(Preformatted(text, self.code))


class GraphHtmlDocBuilder0(HtmlDocBuilder0):
    "A class to write the skeleton of a Python source."

    fileSuffix = '.html'

    def beginModule(self, name, doc, imported):
        # Defer displaying the module header info to later...
        self.shouldDisplayModule = (name, doc, imported)
        self.hasDisplayedModule = 0


    def endModule(self, name, doc, imported):
        if self.hasDisplayedModule:
            HtmlDocBuilder0.endModule(self, name, doc, imported)


    def beginClasses(self, names):
        # Defer displaying the module header info to later...
        if self.shouldDisplayModule:
            self.shouldDisplayClasses = names


    # Skip all methods.
    def beginMethod(self, name, doc, sig):
        pass


    def endMethod(self, name, doc, sig):
        pass


    def beginClass(self, name, doc, bases):
        "Append a graphic demo of a widget at the end of a class."

        aClass = eval('self.skeleton.moduleSpace.' + name)
        if issubclass(aClass, Widget):
            if self.shouldDisplayModule:
                modName, modDoc, imported = self.shouldDisplayModule
                self.outLines.append('<H2>%s</H2>' % modName)
                self.outLines.append('<PRE>%s</PRE>' % modDoc)
                self.shouldDisplayModule = 0
                self.hasDisplayedModule = 1
                if self.shouldDisplayClasses:
                    self.outLines.append('<H2>Classes</H2>')
                    self.shouldDisplayClasses = 0

            HtmlDocBuilder0.beginClass(self, name, doc, bases)


    def endClass(self, name, doc, bases):
        "Append a graphic demo of a widget at the end of a class."

        HtmlDocBuilder0.endClass(self, name, doc, bases)

        aClass = eval('self.skeleton.moduleSpace.' + name)
        if issubclass(aClass, Widget):
            widget = aClass()
            self._showWidgetDemoCode(widget)
            self._showWidgetDemo(widget)
            self._showWidgetProperties(widget)


    def beginFunctions(self, names):
        if string.find(string.join(names, ' '), ' sample') > -1:
            HtmlDocBuilder0.beginFunctions(self, names)


    # Skip non-sample functions.
    def beginFunction(self, name, doc, sig):
        "Skip function for 'uninteresting' names."

        if name[:6] == 'sample':
            HtmlDocBuilder0.beginFunction(self, name, doc, sig)


    def endFunction(self, name, doc, sig):
        "Append a drawing to the story for special function names."

        if name[:6] != 'sample':
            return

        HtmlDocBuilder0.endFunction(self, name, doc, sig)
        aFunc = eval('self.skeleton.moduleSpace.' + name)
        drawing = aFunc()

        self._showFunctionDemoCode(aFunc)
        self._showDrawingDemo(drawing, aFunc.__name__)


    def _showFunctionDemoCode(self, function):
        """Show a demo code of the function generating the drawing."""
        # Heading
        self.outLines.append('<H3>Example</H3>')

        # Sample code
        codeSample = inspect.getsource(function)
        self.outLines.append('<PRE>%s</PRE>' % codeSample)


    def _showDrawingDemo(self, drawing, name):
        """Show a graphical demo of the drawing."""

        # Add the given drawing to the story.
        # Ignored if no GD rendering available
        # or the demo method does not return a drawing.
        try:
            from reportlab.graphics import renderPM
            modName = self.skeleton.getModuleName()
            path = '%s-%s.jpg' % (modName, name)
            renderPM.drawToFile(drawing, path, fmt='JPG')
            self.outLines.append('<H3>Demo</H3>')
            self.outLines.append(makeHtmlInlineImage(path))
        except:
            if VERBOSE:
                print 'caught exception in GraphHTMLDocBuilder._showDrawingDemo'
                traceback.print_exc()
            else:
                pass


    def _showWidgetDemo(self, widget):
        """Show a graphical demo of the widget."""

        # Get a demo drawing from the widget and add it to the story.
        # Ignored if no GD rendering available
        # or the demo method does not return a drawing.
        try:
            from reportlab.graphics import renderPM
            drawing = widget.demo()
            if VERIFY:
                widget.verify()
            modName = self.skeleton.getModuleName()
            path = '%s-%s.jpg' % (modName, widget.__class__.__name__)
            renderPM.drawToFile(drawing, path, fmt='JPG')
            self.outLines.append('<H3>Demo</H3>')
            self.outLines.append(makeHtmlInlineImage(path))
        except:
            if VERBOSE:

                print 'caught exception in GraphHTMLDocBuilder._showWidgetDemo'
                traceback.print_exc()
            else:
                pass


    def _showWidgetDemoCode(self, widget):
        """Show a demo code of the widget."""
        # Heading
        #className = widget.__class__.__name__
        self.outLines.append('<H3>Example Code</H3>')

        # Sample code
        codeSample = inspect.getsource(widget.__class__.demo)
        self.outLines.append('<PRE>%s</PRE>' % codeSample)
        self.outLines.append('')


    def _showWidgetProperties(self, widget):
        """Dump all properties of a widget."""

        props = widget.getProperties()
        keys = props.keys()
        keys.sort()
        lines = []
        for key in keys:
            value = props[key]

            # Method 3
            f = getStringIO()
            pprint.pprint(value, f)
            value = f.getvalue()[:-1]
            valueLines = string.split(value, '\n')
            for i in range(1, len(valueLines)):
                valueLines[i] = ' '*(len(key)+3) + valueLines[i]
            value = string.join(valueLines, '\n')

            lines.append('%s = %s' % (key, value))
        text = join(lines, '\n')
        self.outLines.append('<H3>Properties of Example Widget</H3>')
        self.outLines.append('<PRE>%s</PRE>' % text)
        self.outLines.append('')


# Highly experimental!
class PlatypusDocBuilder0(DocBuilder0):
    "Document the skeleton of a Python module as a Platypus story."

    fileSuffix = '.pps' # A pickled Platypus story.

    def begin(self, name='', typ=''):
        styleSheet = getSampleStyleSheet()
        self.code = styleSheet['Code']
        self.bt = styleSheet['BodyText']
        self.story = []


    def end(self):
        if self.packageName:
            self.outPath = self.packageName + self.fileSuffix
        elif self.skeleton:
            self.outPath = self.skeleton.getModuleName() + self.fileSuffix
        else:
            self.outPath = ''

        if self.outPath:
            f = open(self.outPath, 'w')
            pickle.dump(self.story, f)


    def beginPackage(self, name):
        DocBuilder0.beginPackage(self, name)
        self.story.append(Paragraph(name, self.bt))


    def beginModule(self, name, doc, imported):
        story = self.story
        bt = self.bt

        story.append(Paragraph(name, bt))
        story.append(XPreformatted(doc, bt))


    def beginClasses(self, names):
        self.story.append(Paragraph('Classes', self.bt))


    def beginClass(self, name, doc, bases):
        bt = self.bt
        story = self.story
        if bases:
            bases = map(lambda b:b.__name__, bases) # hack
            story.append(Paragraph('%s(%s)' % (name, join(bases, ', ')), bt))
        else:
            story.append(Paragraph(name, bt))

        story.append(XPreformatted(doc, bt))


    def beginMethod(self, name, doc, sig):
        bt = self.bt
        story = self.story
        story.append(Paragraph(name+sig, bt))
        story.append(XPreformatted(doc, bt))


    def beginFunctions(self, names):
        if names:
            self.story.append(Paragraph('Functions', self.bt))


    def beginFunction(self, name, doc, sig):
        bt = self.bt
        story = self.story
        story.append(Paragraph(name+sig, bt))
        story.append(XPreformatted(doc, bt))


####################################################################
#
# Main
#
####################################################################

def printUsage():
    """graphdocpy.py - Automated documentation for the RL Graphics library.

Usage: python graphdocpy.py [options]

    [options]
        -h          Print this help message.

        -f name     Use the document builder indicated by 'name',
                    e.g. Html, Pdf.

        -m module   Generate document for module named 'module'.
                    'module' may follow any of these forms:
                        - docpy.py
                        - docpy
                        - c:\\test\\docpy
                    and can be any of these:
                        - standard Python modules
                        - modules in the Python search path
                        - modules in the current directory

        -p package  Generate document for package named 'package'
                    (default is 'reportlab.graphics').
                    'package' may follow any of these forms:
                        - reportlab
                        - reportlab.graphics.charts
                        - c:\\test\\reportlab
                    and can be any of these:
                        - standard Python packages (?)
                        - packages in the Python search path
                        - packages in the current directory

        -s          Silent mode (default is unset).

Examples:

    python graphdocpy.py reportlab.graphics
    python graphdocpy.py -m signsandsymbols.py -f Pdf
    python graphdocpy.py -m flags.py -f Html
    python graphdocpy.py -m barchart1.py
"""


# The following functions, including main(), are actually
# the same as in docpy.py (except for some defaults).

def documentModule0(pathOrName, builder, opts={}):
    """Generate documentation for one Python file in some format.

    This handles Python standard modules like string, custom modules
    on the Python search path like e.g. docpy as well as modules
    specified with their full path like C:/tmp/junk.py.

    The doc file will always be saved in the current directory with
    a basename equal to that of the module, e.g. docpy.
    """
    cwd = os.getcwd()

    # Append directory to Python search path if we get one.
    dirName = os.path.dirname(pathOrName)
    if dirName:
        sys.path.append(dirName)

    # Remove .py extension from module name.
    if pathOrName[-3:] == '.py':
        modname = pathOrName[:-3]
    else:
        modname = pathOrName

    # Remove directory paths from module name.
    if dirName:
        modname = os.path.basename(modname)

    # Load the module.
    try:
        module = __import__(modname)
    except:
        print 'Failed to import %s.' % modname
        os.chdir(cwd)
        return

    # Do the real documentation work.
    s = ModuleSkeleton0()
    s.inspect(module)
    builder.write(s)

    # Remove appended directory from Python search path if we got one.
    if dirName:
        del sys.path[-1]

    os.chdir(cwd)


def _packageWalkCallback((builder, opts), dirPath, files):
    "A callback function used when waking over a package tree."
    #must CD into a directory to document the module correctly
    cwd = os.getcwd()
    os.chdir(dirPath)


    # Skip __init__ files.
    files = filter(lambda f:f != '__init__.py', files)

    files = filter(lambda f:f[-3:] == '.py', files)
    for f in files:
        path = os.path.join(dirPath, f)
##        if not opts.get('isSilent', 0):
##            print path
        builder.indentLevel = builder.indentLevel + 1
        #documentModule0(path, builder)
        documentModule0(f, builder)
        builder.indentLevel = builder.indentLevel - 1
    #CD back out
    os.chdir(cwd)

def documentPackage0(pathOrName, builder, opts={}):
    """Generate documentation for one Python package in some format.

    'pathOrName' can be either a filesystem path leading to a Python
    package or package name whose path will be resolved by importing
    the top-level module.

    The doc file will always be saved in the current directory with
    a basename equal to that of the package, e.g. reportlab.lib.
    """

    # Did we get a package path with OS-dependant seperators...?
    if os.sep in pathOrName:
        path = pathOrName
        name = os.path.splitext(os.path.basename(path))[0]
    # ... or rather a package name?
    else:
        name = pathOrName
        package = __import__(name)
        # Some special care needed for dotted names.
        if '.' in name:
            subname = 'package' + name[find(name, '.'):]
            package = eval(subname)
        path = os.path.dirname(package.__file__)

    cwd = os.getcwd()
    os.chdir(path)
    builder.beginPackage(name)
    os.path.walk(path, _packageWalkCallback, (builder, opts))
    builder.endPackage(name)
    os.chdir(cwd)


def makeGraphicsReference(outfilename):
    "Make graphics_reference.pdf"
    builder = GraphPdfDocBuilder0()

    builder.begin(name='reportlab.graphics', typ='package')
    documentPackage0('reportlab.graphics', builder, {'isSilent': 0})
    builder.end(outfilename)
    print 'made graphics reference in %s' % outfilename

def main():
    "Handle command-line options and trigger corresponding action."

    opts, args = getopt.getopt(sys.argv[1:], 'hsf:m:p:')

    # Make an options dictionary that is easier to use.
    optsDict = {}
    for k, v in opts:
        optsDict[k] = v
    hasOpt = optsDict.has_key

    # On -h print usage and exit immediately.
    if hasOpt('-h'):
        print printUsage.__doc__
        sys.exit(0)

    # On -s set silent mode.
    isSilent = hasOpt('-s')

    # On -f set the appropriate DocBuilder to use or a default one.
    builder = { 'Pdf': GraphPdfDocBuilder0,
                'Html': GraphHtmlDocBuilder0,
                }[optsDict.get('-f', 'Pdf')]()

    # Set default module or package to document.
    if not hasOpt('-p') and not hasOpt('-m'):
        optsDict['-p'] = 'reportlab.graphics'

    # Save a few options for further use.
    options = {'isSilent':isSilent}

    # Now call the real documentation functions.
    if hasOpt('-m'):
        nameOrPath = optsDict['-m']
        if not isSilent:
            print "Generating documentation for module %s..." % nameOrPath
        builder.begin(name=nameOrPath, typ='module')
        documentModule0(nameOrPath, builder, options)
    elif hasOpt('-p'):
        nameOrPath = optsDict['-p']
        if not isSilent:
            print "Generating documentation for package %s..." % nameOrPath
        builder.begin(name=nameOrPath, typ='package')
        documentPackage0(nameOrPath, builder, options)
    builder.end()

    if not isSilent:
        print "Saved %s." % builder.outPath

    #if doing the usual, put a copy in docs
    if builder.outPath == 'reportlab.graphics.pdf':
        import shutil, reportlab
        dst = os.path.join(os.path.dirname(reportlab.__file__),'docs','graphics_reference.pdf')
        shutil.copyfile('reportlab.graphics.pdf', dst)
        if not isSilent:
            print 'copied to '+dst

def makeSuite():
    "standard test harness support - run self as separate process"
    from reportlab.test.utils import ScriptThatMakesFileTest
    return ScriptThatMakesFileTest('tools/docco',
                                   'graphdocpy.py',
                                   'reportlab.graphics.pdf')

if __name__ == '__main__':
    main()
