#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_paragraphs.py
# tests some paragraph styles

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.platypus import Paragraph, SimpleDocTemplate, XBox, Indenter, XPreformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import red, black, navy, white, green
from reportlab.lib.randomtext import randomText
from reportlab.rl_config import defaultPageSize

(PAGE_WIDTH, PAGE_HEIGHT) = defaultPageSize


def myFirstPage(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(red)
    canvas.setLineWidth(5)
    canvas.line(66,72,66,PAGE_HEIGHT-72)
    canvas.setFont('Times-Bold',24)
    canvas.drawString(108, PAGE_HEIGHT-54, "TESTING PARAGRAPH STYLES")
    canvas.setFont('Times-Roman',12)
    canvas.drawString(4 * inch, 0.75 * inch, "First Page")
    canvas.restoreState()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(red)
    canvas.setLineWidth(5)
    canvas.line(66,72,66,PAGE_HEIGHT-72)
    canvas.setFont('Times-Roman',12)
    canvas.drawString(4 * inch, 0.75 * inch, "Page %d" % doc.page)
    canvas.restoreState()


class ParagraphTestCase(unittest.TestCase):
    "Test Paragraph class (eyeball-test)."

    def test0(self):
        """Test...

        The story should contain...

        Features to be visually confirmed by a human being are:

            1. ...
            2. ...
            3. ...
        """

        story = []

        #need a style
        styNormal = ParagraphStyle('normal')
        styGreen = ParagraphStyle('green',parent=styNormal,textColor=green)

        # some to test
        stySpaced = ParagraphStyle('spaced',
                                   parent=styNormal,
                                   spaceBefore=12,
                                   spaceAfter=12)


        story.append(
            Paragraph("This is a normal paragraph. "
                      + randomText(), styNormal))
        story.append(
            Paragraph("This has 12 points space before and after, set in the style. "
                      + randomText(), stySpaced))
        story.append(
            Paragraph("This is normal. " +
                      randomText(), styNormal))

        story.append(
            Paragraph("""<para spacebefore="12" spaceafter="12">
            This has 12 points space before and after, set inline with
            XML tag.  It works too.""" + randomText() + "</para",
                      styNormal))

        story.append(
            Paragraph("This is normal. " +
                      randomText(), styNormal))

        styBackground = ParagraphStyle('MyTitle',
                                       fontName='Helvetica-Bold',
                                       fontSize=24,
                                       leading=28,
                                       textColor=white,
                                       backColor=navy)
        story.append(
            Paragraph("This is a title with a background. ", styBackground))

        story.append(
            Paragraph("""<para backcolor="pink">This got a background from the para tag</para>""", styNormal))


        story.append(
            Paragraph("""<para>\n\tThis has newlines and tabs on the front but inside the para tag</para>""", styNormal))
        story.append(
            Paragraph("""<para>  This has spaces on the front but inside the para tag</para>""", styNormal))

        story.append(
            Paragraph("""\n\tThis has newlines and tabs on the front but no para tag""", styNormal))
        story.append(
            Paragraph("""  This has spaces on the front but no para tag""", styNormal))

        story.append(Paragraph("""This has <font color=blue>blue text</font> here.""", styNormal))
        story.append(Paragraph("""This has <i>italic text</i> here.""", styNormal))
        story.append(Paragraph("""This has <b>bold text</b> here.""", styNormal))
        story.append(Paragraph("""This has <u>underlined text</u> here.""", styNormal))
        story.append(Paragraph("""This has <font color=blue><u>blue and <font color=red>red</font> underlined text</u></font> here.""", styNormal))
        story.append(Paragraph("""<u>green underlining</u>""", styGreen))
        story.append(Paragraph("""<u>green <font size=+4><i>underlining</font></i></u>""", styGreen))
        story.append(Paragraph("""This has m<super>2</super> a superscript.""", styNormal))
        story.append(Paragraph("""This has m<sub>2</sub> a subscript. Like H<sub>2</sub>O!""", styNormal))
        story.append(Paragraph("""This has a font change to <font name=Helvetica>Helvetica</font>.""", styNormal))
        #This one fails:
        #story.append(Paragraph("""This has a font change to <font name=Helvetica-Oblique>Helvetica-Oblique</font>.""", styNormal))
        story.append(Paragraph("""This has a font change to <font name=Helvetica><i>Helvetica in italics</i></font>.""", styNormal))

        story.append(Paragraph('''This one uses upper case tags and has set caseSensitive=0: Here comes <FONT FACE="Helvetica" SIZE="14pt">Helvetica 14</FONT> with <STRONG>strong</STRONG> <EM>emphasis</EM>.''', styNormal, caseSensitive=0))
        story.append(Paragraph('''The same as before, but has set not set caseSensitive, thus the tags are ignored: Here comes <FONT FACE="Helvetica" SIZE="14pt">Helvetica 14</FONT> with <STRONG>strong</STRONG> <EM>emphasis</EM>.''', styNormal))
        story.append(Paragraph('''This one uses fonts with size "14pt" and also uses the em and strong tags: Here comes <font face="Helvetica" size="14pt">Helvetica 14</font> with <Strong>strong</Strong> <em>emphasis</em>.''', styNormal, caseSensitive=0))
        story.append(Paragraph('''This uses a font size of 3cm: Here comes <font face="Courier" size="3cm">Courier 3cm</font> and normal again.''', styNormal, caseSensitive=0))
        story.append(Paragraph('''This is just a very long silly text to see if the <FONT face="Courier">caseSensitive</FONT> flag also works if the paragraph is <EM>very</EM> long. '''*20, styNormal, caseSensitive=0))
        story.append(Indenter("1cm"))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Indenter("1cm"))
        story.append(XPreformatted("<para leftIndent='0.5cm' backcolor=pink><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(XPreformatted("<para leftIndent='0.5cm' backcolor=palegreen><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(Indenter("-1cm"))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Indenter("-1cm"))
        story.append(Paragraph("<para>Indented list using seqChain/Format<seqChain order='s0 s1 s2 s3 s4'/><seqReset id='s0'/><seqFormat id='s0' value='1'/><seqFormat id='s1' value='a'/><seqFormat id='s2' value='i'/><seqFormat id='s3' value='A'/><seqFormat id='s4' value='I'/></para>", stySpaced))
        story.append(Indenter("1cm"))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Indenter("1cm"))
        story.append(XPreformatted("<para backcolor=pink><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(XPreformatted("<para backcolor=pink><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(Indenter("-1cm"))
        story.append(Paragraph("<para><bullet bulletIndent='-1cm'><seq id='s0'/>)</bullet>Indented list. %s</para>" % randomText(), styNormal))
        story.append(Indenter("1cm"))
        story.append(XPreformatted("<para backcolor=palegreen><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(Indenter("1cm"))
        story.append(XPreformatted("<para><bullet bulletIndent='-1cm'><seq id='s2'/>)</bullet>Indented list. line1</para>", styNormal))
        story.append(XPreformatted("<para><bullet bulletIndent='-1cm'><seq id='s2'/>)</bullet>Indented list. line2</para>", styNormal))
        story.append(Indenter("-1cm"))
        story.append(XPreformatted("<para backcolor=palegreen><bullet bulletIndent='-1cm'><seq id='s1'/>)</bullet>Indented list.</para>", styNormal))
        story.append(Indenter("-1cm"))
        story.append(Indenter("-1cm"))

        template = SimpleDocTemplate(outputfile('test_paragraphs.pdf'),
                                     showBoundary=1)
        template.build(story,
            onFirstPage=myFirstPage, onLaterPages=myLaterPages)


def makeSuite():
    return makeSuiteForClasses(ParagraphTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
