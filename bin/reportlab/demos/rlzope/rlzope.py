#
# Using the ReportLab toolkit from within Zope
#
# WARNING : The MyPDFDoc class deals with ReportLab's platypus framework,
#       while the MyPageTemplate class directly deals with ReportLab's
#       canvas, this way you know how to do with both...
#
# License : the ReportLab Toolkit's one
#       see : http://www.reportlab.com
#
# Author : Jerome Alet - alet@unice.fr
#
#

import string, cStringIO
try :
    from Shared.reportlab.platypus.paragraph import Paragraph
    from Shared.reportlab.platypus.doctemplate import *
    from Shared.reportlab.lib.units import inch
    from Shared.reportlab.lib import styles
    from Shared.reportlab.lib.utils import ImageReader
except ImportError :
    from reportlab.platypus.paragraph import Paragraph
    from reportlab.platypus.doctemplate import *
    from reportlab.lib.units import inch
    from reportlab.lib import styles
    from reportlab.lib.utils import ImageReader

class MyPDFDoc :
    class MyPageTemplate(PageTemplate) :
        """Our own page template."""
        def __init__(self, parent) :
            """Initialise our page template."""
            #
            # we must save a pointer to our parent somewhere
            self.parent = parent

            # Our doc is made of a single frame
            content = Frame(0.75 * inch, 0.5 * inch, parent.document.pagesize[0] - 1.25 * inch, parent.document.pagesize[1] - (1.5 * inch))
            PageTemplate.__init__(self, "MyTemplate", [content])

            # get all the images we need now, in case we've got
            # several pages this will save some CPU
            self.logo = self.getImageFromZODB("logo")

        def getImageFromZODB(self, name) :
            """Retrieves an Image from the ZODB, converts it to PIL,
               and makes it 0.75 inch high.
            """
            try :
                # try to get it from ZODB
                logo = getattr(self.parent.context, name)
            except AttributeError :
                # not found !
                return None

            # Convert it to PIL
            image = ImageReader(cStringIO.StringIO(str(logo.data)))
            (width, height) = image.getSize()

            # scale it to be 0.75 inch high
            multi = ((height + 0.0) / (0.75 * inch))
            width = int(width / multi)
            height = int(height / multi)

            return ((width, height), image)

        def beforeDrawPage(self, canvas, doc) :
            """Draws a logo and an contribution message on each page."""
            canvas.saveState()
            if self.logo is not None :
                # draws the logo if it exists
                ((width, height), image) = self.logo
                canvas.drawImage(image, inch, doc.pagesize[1] - inch, width, height)
            canvas.setFont('Times-Roman', 10)
            canvas.drawCentredString(inch + (doc.pagesize[0] - (1.5 * inch)) / 2, 0.25 * inch, "Contributed by Jerome Alet - alet@unice.fr")
            canvas.restoreState()

    def __init__(self, context, filename) :
        # save some datas
        self.context = context
        self.built = 0
        self.objects = []

        # we will build an in-memory document
        # instead of creating an on-disk file.
        self.report = cStringIO.StringIO()

        # initialise a PDF document using ReportLab's platypus
        self.document = BaseDocTemplate(self.report)

        # add our page template
        # (we could add more than one, but I prefer to keep it simple)
        self.document.addPageTemplates(self.MyPageTemplate(self))

        # get the default style sheets
        self.StyleSheet = styles.getSampleStyleSheet()

        # then build a simple doc with ReportLab's platypus
        sometext = "A sample script to show how to use ReportLab from within Zope"
        url = self.escapexml(context.absolute_url())
        urlfilename = self.escapexml(context.absolute_url() + '/%s' % filename)
        self.append(Paragraph("Using ReportLab from within Zope", self.StyleSheet["Heading3"]))
        self.append(Spacer(0, 10))
        self.append(Paragraph("You launched it from : %s" % url, self.StyleSheet['Normal']))
        self.append(Spacer(0, 40))
        self.append(Paragraph("If possible, this report will be automatically saved as : %s" % urlfilename, self.StyleSheet['Normal']))

        # generation du document PDF
        self.document.build(self.objects)
        self.built = 1

    def __str__(self) :
        """Returns the PDF document as a string of text, or None if it's not ready yet."""
        if self.built :
            return self.report.getvalue()
        else :
            return None

    def append(self, object) :
        """Appends an object to our platypus "story" (using ReportLab's terminology)."""
        self.objects.append(object)

    def escapexml(self, s) :
        """Escape some xml entities."""
        s = string.strip(s)
        s = string.replace(s, "&", "&amp;")
        s = string.replace(s, "<", "&lt;")
        return string.replace(s, ">", "&gt;")

def rlzope(self) :
    """A sample external method to show people how to use ReportLab from within Zope."""
    try:
        #
        # which file/object name to use ?
        # append ?name=xxxxx to rlzope's url to
        # choose another name
        filename = self.REQUEST.get("name", "dummy.pdf")
        if filename[-4:] != '.pdf' :
            filename = filename + '.pdf'

        # tell the browser we send some PDF document
        # with the requested filename

        # get the document's content itself as a string of text
        content = str(MyPDFDoc(self, filename))

        # we will return it to the browser, but before that we also want to
        # save it into the ZODB into the current folder
        try :
            self.manage_addFile(id = filename, file = content, title = "A sample PDF document produced with ReportLab", precondition = '', content_type = "application/pdf")
        except :
            # it seems an object with this name already exists in the ZODB:
            # it's more secure to not replace it, since we could possibly
            # destroy an important PDF document of this name.
            pass
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'application/pdf')
        self.REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    except:
        import traceback, sys, cgi
        content = sys.stdout = sys.stderr = cStringIO.StringIO()
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/html')
        traceback.print_exc()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        content = '<html><head></head><body><pre>%s</pre></body></html>' % cgi.escape(content.getvalue())

    # then we also return the PDF content to the browser
    return content
