#!/usr/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/docpy.py

"""Generate documentation from live Python objects.

This is an evolving module that allows to generate documentation
for python modules in an automated fashion. The idea is to take
live Python objects and inspect them in order to use as much mean-
ingful information as possible to write in some formatted way into
different types of documents.

In principle a skeleton captures the gathered information and
makes it available via a certain API to formatters that use it
in whatever way they like to produce something of interest. The
API allows for adding behaviour in subclasses of these formatters,
such that, e.g. for certain classes it is possible to trigger
special actions like displaying a sample image of a class that
represents some graphical widget, say.

Type the following for usage info:

  python docpy.py -h
"""

# Much inspired by Ka-Ping Yee's htmldoc.py.
# Needs the inspect module.

# Dinu Gherman


__version__ = '0.8'


import sys, os, re, types, string, getopt, copy, time
from string import find, join, split, replace, expandtabs, rstrip

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import A4
from reportlab.lib import enums
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.flowables import Flowable, Spacer
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.flowables \
     import Flowable, Preformatted,Spacer, Image, KeepTogether, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.xpreformatted import XPreformatted
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate \
     import PageTemplate, BaseDocTemplate
from reportlab.platypus.tables import TableStyle, Table
import inspect

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
            headerline = string.join(canvas.headerLine, ' \215 ') # bullet
            canvas.drawString(2*cm, A4[1]-1.75*cm, headerline)

    canvas.setFont('Times-Roman', 8)
    msg = "Generated with reportlab.lib.docpy. See http://www.reportlab.com!"
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
            name7 = f.style.name[:7]
            name8 = f.style.name[:8]

            # Build a list of heading parts.
            # So far, this is the *last* item on the *previous* page...
            if name7 == 'Heading' and not hasattr(self.canv, 'headerLine'):
                self.canv.headerLine = []

            if name8 == 'Heading0':
                self.canv.headerLine = [f.text] # hackish
            elif name8 == 'Heading1':
                if len(self.canv.headerLine) == 2:
                    del self.canv.headerLine[-1]
                elif len(self.canv.headerLine) == 3:
                    del self.canv.headerLine[-1]
                    del self.canv.headerLine[-1]
                self.canv.headerLine.append(f.text)
            elif name8 == 'Heading2':
                if len(self.canv.headerLine) == 3:
                    del self.canv.headerLine[-1]
                self.canv.headerLine.append(f.text)

            if name7 == 'Heading':
                # Register TOC entries.
                headLevel = int(f.style.name[7:])
                self.notify('TOCEntry', (headLevel, flowable.getPlainText(), self.page))

                # Add PDF outline entries.
                c = self.canv
                title = f.text
                key = str(hash(f))

                try:
                    if headLevel == 0:
                        isClosed = 0
                    else:
                        isClosed = 1

                    c.bookmarkPage(key)
                    c.addOutlineEntry(title, key, level=headLevel,
                                      closed=isClosed)
                except ValueError:
                    pass


####################################################################
#
# Utility functions (Ka-Ping Yee).
#
####################################################################

def htmlescape(text):
    "Escape special HTML characters, namely &, <, >."
    return replace(replace(replace(text, '&', '&amp;'),
                                         '<', '&lt;'),
                                         '>', '&gt;')

def htmlrepr(object):
    return htmlescape(repr(object))


def defaultformat(object):
    return '=' + htmlrepr(object)


def getdoc(object):
    result = inspect.getdoc(object)
    if not result:
        try:
            result = inspect.getcomments(object)
        except:
            pass
    return result and rstrip(result) + '\n' or ''


def reduceDocStringLength(docStr):
    "Return first line of a multiline string."

    return split(docStr, '\n')[0]


####################################################################
#
# More utility functions
#
####################################################################

def makeHtmlSection(text, bgcolor='#FFA0FF'):
    """Create HTML code for a section.

    This is usually a header for all classes or functions.
u    """
    text = htmlescape(expandtabs(text))
    result = []
    result.append("""<TABLE WIDTH="100\%" BORDER="0">""")
    result.append("""<TR><TD BGCOLOR="%s" VALIGN="CENTER">""" % bgcolor)
    result.append("""<H2>%s</H2>""" % text)
    result.append("""</TD></TR></TABLE>""")
    result.append('')

    return join(result, '\n')


def makeHtmlSubSection(text, bgcolor='#AAA0FF'):
    """Create HTML code for a subsection.

    This is usually a class or function name.
    """
    text = htmlescape(expandtabs(text))
    result = []
    result.append("""<TABLE WIDTH="100\%" BORDER="0">""")
    result.append("""<TR><TD BGCOLOR="%s" VALIGN="CENTER">""" % bgcolor)
    result.append("""<H3><TT><FONT SIZE="+2">%s</FONT></TT></H3>""" % text)
    result.append("""</TD></TR></TABLE>""")
    result.append('')

    return join(result, '\n')


def makeHtmlInlineImage(text):
    """Create HTML code for an inline image.
    """

    return """<IMG SRC="%s" ALT="%s">""" % (text, text)


####################################################################
#
# Core "standard" docpy classes
#
####################################################################

class PackageSkeleton0:
    """A class collecting 'interesting' information about a package."""
    pass # Not yet!


class ModuleSkeleton0:
    """A class collecting 'interesting' information about a module."""

    def __init__(self):
        # This is an ad-hoc, somewhat questionable 'data structure',
        # but for the time being it serves its purpose and is fairly
        # self-contained.
        self.module = {}
        self.functions = {}
        self.classes = {}


    # Might need more like this, later.
    def getModuleName(self):
        """Return the name of the module being treated."""

        return self.module['name']


    # These inspect methods all rely on the inspect module.
    def inspect(self, object):
        """Collect information about a given object."""

        self.moduleSpace = object

        # Very non-OO, left for later...
        if inspect.ismodule(object):
            self._inspectModule(object)
        elif inspect.isclass(object):
            self._inspectClass(object)
        elif inspect.ismethod(object):
            self._inspectMethod(object)
        elif inspect.isfunction(object):
            self._inspectFunction(object)
        elif inspect.isbuiltin(object):
            self._inspectBuiltin(object)
        else:
            msg = "Don't know how to document this kind of object."
            raise TypeError, msg


    def _inspectModule(self, object):
        """Collect information about a given module object."""
        name = object.__name__

        self.module['name'] = name
        if hasattr(object, '__version__'):
            self.module['version'] = object.__version__

        cadr = lambda list: list[1]
        modules = map(cadr, inspect.getmembers(object, inspect.ismodule))

        classes, cdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isclass):
            if (inspect.getmodule(value) or object) is object:
                classes.append(value)
                cdict[key] = cdict[value] = '#' + key

        functions, fdict = [], {}
        for key, value in inspect.getmembers(object, inspect.isroutine):
            #if inspect.isbuiltin(value) or inspect.getmodule(value) is object:
            functions.append(value)
            fdict[key] = '#-' + key
            if inspect.isfunction(value): fdict[value] = fdict[key]

        for c in classes:
            for base in c.__bases__:
                key, modname = base.__name__, base.__module__
                if modname != name and sys.modules.has_key(modname):
                    module = sys.modules[modname]
                    if hasattr(module, key) and getattr(module, key) is base:
                        if not cdict.has_key(key):
                            cdict[key] = cdict[base] = modname + '.txt#' + key

##        doc = getdoc(object) or 'No doc string.'
        doc = getdoc(object)
        self.module['doc'] = doc

        if modules:
            self.module['importedModules'] = map(lambda m:m.__name__, modules)

        if classes:
            for item in classes:
                self._inspectClass(item, fdict, cdict)

        if functions:
            for item in functions:
                self._inspectFunction(item, fdict, cdict)


    def _inspectClass(self, object, functions={}, classes={}):
        """Collect information about a given class object."""

        name = object.__name__
        bases = object.__bases__
        results = []

        if bases:
            parents = []
            for base in bases:
                parents.append(base)

        self.classes[name] = {}
        if bases:
            self.classes[name]['bases'] = parents

        methods, mdict = [], {}
        for key, value in inspect.getmembers(object, inspect.ismethod):
            methods.append(value)
            mdict[key] = mdict[value] = '#' + name + '-' + key

        if methods:
            if not self.classes[name].has_key('methods'):
                self.classes[name]['methods'] = {}
            for item in methods:
                self._inspectMethod(item, functions, classes, mdict, name)

##        doc = getdoc(object) or 'No doc string.'
        doc = getdoc(object)
        self.classes[name]['doc'] = doc


    def _inspectMethod(self, object, functions={}, classes={}, methods={}, clname=''):
        """Collect information about a given method object."""

        self._inspectFunction(object.im_func, functions, classes, methods, clname)


    def _inspectFunction(self, object, functions={}, classes={}, methods={}, clname=''):
        """Collect information about a given function object."""
        try:
            args, varargs, varkw, defaults = inspect.getargspec(object)
            argspec = inspect.formatargspec(
                args, varargs, varkw, defaults,
                defaultformat=defaultformat)
        except TypeError:
            argspec = '( ... )'

##        doc = getdoc(object) or 'No doc string.'
        doc = getdoc(object)

        if object.__name__ == '<lambda>':
            decl = [' lambda  ', argspec[1:-1]]
            # print '  %s' % decl
            # Do something with lambda functions as well...
            # ...
        else:
            decl = object.__name__
            if not clname:
                self.functions[object.__name__] = {'signature':argspec, 'doc':doc}
            else:
                theMethods = self.classes[clname]['methods']
                if not theMethods.has_key(object.__name__):
                    theMethods[object.__name__] = {}

                theMethod = theMethods[object.__name__]
                theMethod['signature'] = argspec
                theMethod['doc'] = doc


    def _inspectBuiltin(self, object):
        """Collect information about a given built-in."""

        print object.__name__ + '( ... )'


    def walk(self, formatter):
        """Call event methods in a visiting formatter."""

        s = self
        f = formatter

        # The order is fixed, but could be made flexible
        # with one more template method...

        # Module
        modName = s.module['name']
        modDoc = s.module['doc']
        imported = s.module.get('importedModules', [])
        imported.sort()
        # f.indentLevel = f.indentLevel + 1
        f.beginModule(modName, modDoc, imported)

        # Classes
        f.indentLevel = f.indentLevel + 1
        f.beginClasses(s.classes.keys())
        items = s.classes.items()
        items.sort()
        for k, v in items:
            cDoc = s.classes[k]['doc']
            bases = s.classes[k].get('bases', [])
            f.indentLevel = f.indentLevel + 1
            f.beginClass(k, cDoc, bases)

            # This if should move out of this method.
            if not s.classes[k].has_key('methods'):
                s.classes[k]['methods'] = {}

            # Methods
            #f.indentLevel = f.indentLevel + 1
            f.beginMethods(s.classes[k]['methods'].keys())
            items = s.classes[k]['methods'].items()
            items.sort()
            for m, v in items:
                mDoc = v['doc']
                sig = v['signature']
                f.indentLevel = f.indentLevel + 1
                f.beginMethod(m, mDoc, sig)
                f.indentLevel = f.indentLevel - 1
                f.endMethod(m, mDoc, sig)

            #f.indentLevel = f.indentLevel - 1
            f.endMethods(s.classes[k]['methods'].keys())

            f.indentLevel = f.indentLevel - 1
            f.endClass(k, cDoc, bases)

            # And what about attributes?!

        f.indentLevel = f.indentLevel - 1
        f.endClasses(s.classes.keys())

        # Functions
        f.indentLevel = f.indentLevel + 1
        f.beginFunctions(s.functions.keys())
        items = s.functions.items()
        items.sort()
        for k, v in items:
            doc = v['doc']
            sig = v['signature']
            f.indentLevel = f.indentLevel + 1
            f.beginFunction(k, doc, sig)
            f.indentLevel = f.indentLevel - 1
            f.endFunction(k, doc, sig)
        f.indentLevel = f.indentLevel - 1
        f.endFunctions(s.functions.keys())

        #f.indentLevel = f.indentLevel - 1
        f.endModule(modName, modDoc, imported)

        # Constants?!


####################################################################
#
# Core "standard" docpy document builders
#
####################################################################

class DocBuilder0:
    """An abstract class to document the skeleton of a Python module.

    Instances take a skeleton instance s and call their s.walk()
    method. The skeleton, in turn, will walk over its tree structure
    while generating events and calling equivalent methods from a
    specific interface (begin/end methods).
    """

    fileSuffix = None

    def __init__(self, skeleton=None):
        self.skeleton = skeleton
        self.packageName = None
        self.indentLevel = 0


    def write(self, skeleton=None):
        if skeleton:
            self.skeleton = skeleton
        self.skeleton.walk(self)


    # Event-method API, called by associated skeleton instances.
    # In fact, these should raise a NotImplementedError, but for now we
    # just don't do anything here.

    # The following four methods are *not* called by skeletons!
    def begin(self, name='', typ=''): pass
    def end(self): pass

    # Methods for packaging should move into a future PackageSkeleton...
    def beginPackage(self, name):
        self.packageName = name

    def endPackage(self, name):
        pass

    # Only this subset is really called by associated skeleton instances.

    def beginModule(self, name, doc, imported): pass
    def endModule(self, name, doc, imported): pass

    def beginClasses(self, names): pass
    def endClasses(self, names): pass

    def beginClass(self, name, doc, bases): pass
    def endClass(self, name, doc, bases): pass

    def beginMethods(self, names): pass
    def endMethods(self, names): pass

    def beginMethod(self, name, doc, sig): pass
    def endMethod(self, name, doc, sig): pass

    def beginFunctions(self, names): pass
    def endFunctions(self, names): pass

    def beginFunction(self, name, doc, sig): pass
    def endFunction(self, name, doc, sig): pass


class AsciiDocBuilder0(DocBuilder0):
    """Document the skeleton of a Python module in ASCII format.

    The output will be an ASCII file with nested lines representing
    the hiearchical module structure.

    Currently, no doc strings are listed.
    """

    fileSuffix = '.txt'
    outLines = []
    indentLabel = '  '

    def end(self):
        # This if should move into DocBuilder0...
        if self.packageName:
            self.outPath = self.packageName + self.fileSuffix
        elif self.skeleton:
            self.outPath = self.skeleton.getModuleName() + self.fileSuffix
        else:
            self.outPath = ''

        if self.outPath:
            file = open(self.outPath, 'w')
            for line in self.outLines:
                file.write(line + '\n')
            file.close()


    def beginPackage(self, name):
        DocBuilder0.beginPackage(self, name)
        lev, label = self.indentLevel, self.indentLabel
        self.outLines.append('%sPackage: %s' % (lev*label, name))
        self.outLines.append('')


    def beginModule(self, name, doc, imported):
        append = self.outLines.append
        lev, label = self.indentLevel, self.indentLabel
        self.outLines.append('%sModule: %s' % (lev*label, name))
##        self.outLines.append('%s%s' % ((lev+1)*label, reduceDocStringLength(doc)))
        append('')

        if imported:
            self.outLines.append('%sImported' % ((lev+1)*label))
            append('')
            for m in imported:
                self.outLines.append('%s%s' % ((lev+2)*label, m))
            append('')


    def beginClasses(self, names):
        if names:
            lev, label = self.indentLevel, self.indentLabel
            self.outLines.append('%sClasses' % (lev*label))
            self.outLines.append('')


    def beginClass(self, name, doc, bases):
        append = self.outLines.append
        lev, label = self.indentLevel, self.indentLabel

        if bases:
            bases = map(lambda b:b.__name__, bases) # hack
            append('%s%s(%s)' % (lev*label, name, join(bases, ', ')))
        else:
            append('%s%s' % (lev*label, name))
        return

##        append('%s%s' % ((lev+1)*label, reduceDocStringLength(doc)))
        self.outLines.append('')


    def endClass(self, name, doc, bases):
        self.outLines.append('')


    def beginMethod(self, name, doc, sig):
        append = self.outLines.append
        lev, label = self.indentLevel, self.indentLabel
        append('%s%s%s' % (lev*label, name, sig))
##        append('%s%s' % ((lev+1)*label, reduceDocStringLength(doc)))
##        append('')


    def beginFunctions(self, names):
        if names:
            lev, label = self.indentLevel, self.indentLabel
            self.outLines.append('%sFunctions' % (lev*label))
            self.outLines.append('')


    def endFunctions(self, names):
        self.outLines.append('')


    def beginFunction(self, name, doc, sig):
        append = self.outLines.append
        lev, label = self.indentLevel, self.indentLabel
        self.outLines.append('%s%s%s' % (lev*label, name, sig))
##        append('%s%s' % ((lev+1)*label, reduceDocStringLength(doc)))
##        append('')


class HtmlDocBuilder0(DocBuilder0):
    "A class to write the skeleton of a Python source in HTML format."

    fileSuffix = '.html'
    outLines = []

    def begin(self, name='', typ=''):
        self.outLines.append("""<!doctype html public "-//W3C//DTD HTML 4.0 Transitional//EN">""")
        self.outLines.append("""<html>""")


    def end(self):
        if self.packageName:
            self.outPath = self.packageName + self.fileSuffix
        elif self.skeleton:
            self.outPath = self.skeleton.getModuleName() + self.fileSuffix
        else:
            self.outPath = ''

        if self.outPath:
            file = open(self.outPath, 'w')
            self.outLines.append('</body></html>')
            for line in self.outLines:
                file.write(line + '\n')
            file.close()


    def beginPackage(self, name):
        DocBuilder0.beginPackage(self, name)

        self.outLines.append("""<title>%s</title>""" % name)
        self.outLines.append("""<body bgcolor="#ffffff">""")
        self.outLines.append("""<H1>%s</H1>""" % name)
        self.outLines.append('')


    def beginModule(self, name, doc, imported):
        if not self.packageName:
            self.outLines.append("""<title>%s</title>""" % name)
            self.outLines.append("""<body bgcolor="#ffffff">""")

        self.outLines.append("""<H1>%s</H1>""" % name)
        self.outLines.append('')
        for line in split(doc, '\n'):
            self.outLines.append("""<FONT SIZE="-1">%s</FONT>""" % htmlescape(line))
            self.outLines.append('<BR>')
        self.outLines.append('')

        if imported:
            self.outLines.append(makeHtmlSection('Imported Modules'))
            self.outLines.append("""<ul>""")
            for m in imported:
                self.outLines.append("""<li>%s</li>""" % m)
            self.outLines.append("""</ul>""")


    def beginClasses(self, names):
        self.outLines.append(makeHtmlSection('Classes'))


    def beginClass(self, name, doc, bases):
        DocBuilder0.beginClass(self, name, doc, bases)

##        # Keep an eye on the base classes.
##        self.currentBaseClasses = bases

        if bases:
            bases = map(lambda b:b.__name__, bases) # hack
            self.outLines.append(makeHtmlSubSection('%s(%s)' % (name, join(bases, ', '))))
        else:
            self.outLines.append(makeHtmlSubSection('%s' % name))
        for line in split(doc, '\n'):
            self.outLines.append("""<FONT SIZE="-1">%s</FONT>""" % htmlescape(line))
            self.outLines.append('<BR>')

        self.outLines.append('')


    def beginMethods(self, names):
        pass
##        if names:
##            self.outLines.append('<H3>Method Interface</H3>')
##            self.outLines.append('')


    def beginMethod(self, name, doc, sig):
        self.beginFunction(name, doc, sig)


    def beginFunctions(self, names):
        self.outLines.append(makeHtmlSection('Functions'))


    def beginFunction(self, name, doc, sig):
        append = self.outLines.append
        append("""<DL><DL><DT><TT><STRONG>%s</STRONG>%s</TT></DT>""" % (name, sig))
        append('')
        for line in split(doc, '\n'):
            append("""<DD><FONT SIZE="-1">%s</FONT></DD>""" % htmlescape(line))
            append('<BR>')
        append('</DL></DL>')
        append('')


class PdfDocBuilder0(DocBuilder0):
    "Document the skeleton of a Python module in PDF format."

    fileSuffix = '.pdf'

    def makeHeadingStyle(self, level, typ=None, doc=''):
        "Make a heading style for different types of module content."

        if typ in ('package', 'module', 'class'):
            style = ParagraphStyle(name='Heading'+str(level),
                                      fontName = 'Courier-Bold',
                                      fontSize=14,
                                      leading=18,
                                      spaceBefore=12,
                                      spaceAfter=6)
        elif typ in ('method', 'function'):
            if doc:
                style = ParagraphStyle(name='Heading'+str(level),
                                          fontName = 'Courier-Bold',
                                          fontSize=12,
                                          leading=18,
                                          firstLineIndent=-18,
                                          leftIndent=36,
                                          spaceBefore=0,
                                          spaceAfter=-3)
            else:
                style = ParagraphStyle(name='Heading'+str(level),
                                          fontName = 'Courier-Bold',
                                          fontSize=12,
                                          leading=18,
                                          firstLineIndent=-18,
                                          leftIndent=36,
                                          spaceBefore=0,
                                          spaceAfter=0)

        else:
            style = ParagraphStyle(name='Heading'+str(level),
                                      fontName = 'Times-Bold',
                                      fontSize=14,
                                      leading=18,
                                      spaceBefore=12,
                                      spaceAfter=6)

        return style


    def begin(self, name='', typ=''):
        styleSheet = getSampleStyleSheet()
        self.code = styleSheet['Code']
        self.bt = styleSheet['BodyText']
        self.story = []

        # Cover page
        t = time.gmtime(time.time())
        timeString = time.strftime("%Y-%m-%d %H:%M", t)
        self.story.append(Paragraph('<font size=18>Documentation for %s "%s"</font>' % (typ, name), self.bt))
        self.story.append(Paragraph('<font size=18>Generated by: docpy.py version %s</font>' %  __version__, self.bt))
        self.story.append(Paragraph('<font size=18>Date generated: %s</font>' % timeString, self.bt))
        self.story.append(Paragraph('<font size=18>Format: PDF</font>', self.bt))
        self.story.append(PageBreak())

        # Table of contents
        toc = TableOfContents()
        self.story.append(toc)
        self.story.append(PageBreak())


    def end(self):
        if self.outPath is not None:
            pass
        elif self.packageName:
            self.outPath = self.packageName + self.fileSuffix
        elif self.skeleton:
            self.outPath = self.skeleton.getModuleName() + self.fileSuffix
        else:
            self.outPath = ''
        print 'output path is %s' % self.outPath
        if self.outPath:
            doc = MyTemplate(self.outPath)
            doc.multiBuild(self.story)


    def beginPackage(self, name):
        DocBuilder0.beginPackage(self, name)
        story = self.story
        story.append(Paragraph(name, self.makeHeadingStyle(self.indentLevel, 'package')))


    def beginModule(self, name, doc, imported):
        story = self.story
        bt = self.bt
        story.append(Paragraph(name, self.makeHeadingStyle(self.indentLevel, 'module')))
        if doc:
            story.append(XPreformatted(htmlescape(doc), bt))
            story.append(XPreformatted('', bt))

        if imported:
            story.append(Paragraph('Imported modules', self.makeHeadingStyle(self.indentLevel + 1)))
            for m in imported:
                p = Paragraph('<bullet>\201</bullet> %s' % m, bt)
                p.style.bulletIndent = 10
                p.style.leftIndent = 18
                story.append(p)


    def endModule(self, name, doc, imported):
        DocBuilder0.endModule(self, name, doc, imported)
        self.story.append(PageBreak())


    def beginClasses(self, names):
        self.story.append(Paragraph('Classes', self.makeHeadingStyle(self.indentLevel)))


    def beginClass(self, name, doc, bases):
        bt = self.bt
        story = self.story
        if bases:
            bases = map(lambda b:b.__name__, bases) # hack
            story.append(Paragraph('%s(%s)' % (name, join(bases, ', ')), self.makeHeadingStyle(self.indentLevel, 'class')))
        else:
            story.append(Paragraph(name, self.makeHeadingStyle(self.indentLevel, 'class')))

        if doc:
            story.append(XPreformatted(htmlescape(doc), bt))
            story.append(XPreformatted('', bt))


    def beginMethod(self, name, doc, sig):
        bt = self.bt
        story = self.story
        story.append(Paragraph(name+sig, self.makeHeadingStyle(self.indentLevel, 'method', doc)))
        if doc:
            story.append(XPreformatted(htmlescape(doc), bt))
            story.append(XPreformatted('', bt))


    def beginFunctions(self, names):
        if names:
            self.story.append(Paragraph('Functions', self.makeHeadingStyle(self.indentLevel)))


    def beginFunction(self, name, doc, sig):
        bt = self.bt
        story = self.story
        story.append(Paragraph(name+sig, self.makeHeadingStyle(self.indentLevel, 'function')))
        if doc:
            story.append(XPreformatted(htmlescape(doc), bt))
            story.append(XPreformatted('', bt))


class UmlPdfDocBuilder0(PdfDocBuilder0):
    "Document the skeleton of a Python module with UML class diagrams."

    fileSuffix = '.pdf'

    def begin(self, name='', typ=''):
        styleSheet = getSampleStyleSheet()
        self.h1 = styleSheet['Heading1']
        self.h2 = styleSheet['Heading2']
        self.h3 = styleSheet['Heading3']
        self.code = styleSheet['Code']
        self.bt = styleSheet['BodyText']
        self.story = []
        self.classCompartment = ''
        self.methodCompartment = []


    def beginModule(self, name, doc, imported):
        story = self.story
        h1, h2, h3, bt = self.h1, self.h2, self.h3, self.bt
        styleSheet = getSampleStyleSheet()
        bt1 = styleSheet['BodyText']

        story.append(Paragraph(name, h1))
        story.append(XPreformatted(doc, bt1))

        if imported:
            story.append(Paragraph('Imported modules', self.makeHeadingStyle(self.indentLevel + 1)))
            for m in imported:
                p = Paragraph('<bullet>\201</bullet> %s' % m, bt1)
                p.style.bulletIndent = 10
                p.style.leftIndent = 18
                story.append(p)


    def endModule(self, name, doc, imported):
        self.story.append(PageBreak())
        PdfDocBuilder0.endModule(self, name, doc, imported)


    def beginClasses(self, names):
        h1, h2, h3, bt = self.h1, self.h2, self.h3, self.bt
        if names:
            self.story.append(Paragraph('Classes', h2))


    def beginClass(self, name, doc, bases):
        self.classCompartment = ''
        self.methodCompartment = []

        if bases:
            bases = map(lambda b:b.__name__, bases) # hack
            self.classCompartment = '%s(%s)' % (name, join(bases, ', '))
        else:
            self.classCompartment = name


    def endClass(self, name, doc, bases):
        h1, h2, h3, bt, code = self.h1, self.h2, self.h3, self.bt, self.code
        styleSheet = getSampleStyleSheet()
        bt1 = styleSheet['BodyText']
        story = self.story

        # Use only the first line of the class' doc string --
        # no matter how long! (Do the same later for methods)
        classDoc = reduceDocStringLength(doc)

        tsa = tableStyleAttributes = []

        # Make table with class and method rows
        # and add it to the story.
        p = Paragraph('<b>%s</b>' % self.classCompartment, bt)
        p.style.alignment = TA_CENTER
        rows = [(p,)]
        # No doc strings, now...
        # rows = rows + [(Paragraph('<i>%s</i>' % classDoc, bt1),)]
        lenRows = len(rows)
        tsa.append(('BOX', (0,0), (-1,lenRows-1), 0.25, colors.black))
        for name, doc, sig in self.methodCompartment:
            nameAndSig = Paragraph('<b>%s</b>%s' % (name, sig), bt1)
            rows.append((nameAndSig,))
            # No doc strings, now...
            # docStr = Paragraph('<i>%s</i>' % reduceDocStringLength(doc), bt1)
            # rows.append((docStr,))
        tsa.append(('BOX', (0,lenRows), (-1,-1), 0.25, colors.black))
        t = Table(rows, (12*cm,))
        tableStyle = TableStyle(tableStyleAttributes)
        t.setStyle(tableStyle)
        self.story.append(t)
        self.story.append(Spacer(1*cm, 1*cm))


    def beginMethod(self, name, doc, sig):
        self.methodCompartment.append((name, doc, sig))


    def beginFunctions(self, names):
        h1, h2, h3, bt = self.h1, self.h2, self.h3, self.bt
        if names:
            self.story.append(Paragraph('Functions', h2))
        self.classCompartment = chr(171) + ' Module-Level Functions ' + chr(187)
        self.methodCompartment = []


    def beginFunction(self, name, doc, sig):
        self.methodCompartment.append((name, doc, sig))


    def endFunctions(self, names):
        h1, h2, h3, bt, code = self.h1, self.h2, self.h3, self.bt, self.code
        styleSheet = getSampleStyleSheet()
        bt1 = styleSheet['BodyText']
        story = self.story
        if not names:
            return

        tsa = tableStyleAttributes = []

        # Make table with class and method rows
        # and add it to the story.
        p = Paragraph('<b>%s</b>' % self.classCompartment, bt)
        p.style.alignment = TA_CENTER
        rows = [(p,)]
        lenRows = len(rows)
        tsa.append(('BOX', (0,0), (-1,lenRows-1), 0.25, colors.black))
        for name, doc, sig in self.methodCompartment:
            nameAndSig = Paragraph('<b>%s</b>%s' % (name, sig), bt1)
            rows.append((nameAndSig,))
            # No doc strings, now...
            # docStr = Paragraph('<i>%s</i>' % reduceDocStringLength(doc), bt1)
            # rows.append((docStr,))
        tsa.append(('BOX', (0,lenRows), (-1,-1), 0.25, colors.black))
        t = Table(rows, (12*cm,))
        tableStyle = TableStyle(tableStyleAttributes)
        t.setStyle(tableStyle)
        self.story.append(t)
        self.story.append(Spacer(1*cm, 1*cm))


####################################################################
#
# Main
#
####################################################################

def printUsage():
    """docpy.py - Automated documentation for Python source code.

Usage: python docpy.py [options]

    [options]
        -h          Print this help message.

        -f name     Use the document builder indicated by 'name',
                    e.g. Ascii, Html, Pdf (default), UmlPdf.

        -m module   Generate document for module named 'module'
                    (default is 'docpy').
                    'module' may follow any of these forms:
                        - docpy.py
                        - docpy
                        - c:\\test\\docpy
                    and can be any of these:
                        - standard Python modules
                        - modules in the Python search path
                        - modules in the current directory

        -p package  Generate document for package named 'package'.
                    'package' may follow any of these forms:
                        - reportlab
                        - reportlab.platypus
                        - c:\\test\\reportlab
                    and can be any of these:
                        - standard Python packages (?)
                        - packages in the Python search path
                        - packages in the current directory

        -s          Silent mode (default is unset).

Examples:

    python docpy.py -h
    python docpy.py -m docpy.py -f Ascii
    python docpy.py -m string -f Html
    python docpy.py -m signsandsymbols.py -f Pdf
    python docpy.py -p reportlab.platypus -f UmlPdf
    python docpy.py -p reportlab.lib -s -f UmlPdf
"""


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

    # Skip __init__ files.
    files = filter(lambda f:f != '__init__.py', files)

    files = filter(lambda f:f[-3:] == '.py', files)
    for f in files:
        path = os.path.join(dirPath, f)
        if not opts.get('isSilent', 0):
            print path
        builder.indentLevel = builder.indentLevel + 1
        documentModule0(path, builder)
        builder.indentLevel = builder.indentLevel - 1


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
    builder.beginPackage(name)
    os.path.walk(path, _packageWalkCallback, (builder, opts))
    builder.endPackage(name)
    os.chdir(cwd)


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
    builderClassName = optsDict.get('-f', 'Pdf') + 'DocBuilder0'
    builder = eval(builderClassName + '()')

    # Set default module or package to document.
    if not hasOpt('-p') and not hasOpt('-m'):
        optsDict['-m'] = 'docpy'

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


if __name__ == '__main__':
    main()
