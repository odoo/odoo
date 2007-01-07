#Copyright ReportLab Europe Ltd. 2000-2004
#this test and associates functionality kinds donated by Ian Sparks.
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_pdfgen_links.py
"""
Tests for internal links and destinations
"""

#
# Fit tests
#
# Modification History
# ====================
#
# 11-Mar-2003 Ian Sparks
#   * Initial version.
#
#
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

def markPage(c,height=letter[1],width=letter[0]):
    height = height / inch
    width = width / inch
    for y in range(int(height)):
        for x in range(int(width)):
            c.drawString(x*inch,y*inch,"x=%d y=%d" % (x,y) )
            c.line(x*inch,0,x*inch,height*inch)
            c.line(0,y*inch,width*inch,y*inch)

fn = outputfile("test_pdfgen_links.pdf")


class LinkTestCase(unittest.TestCase):
    "Test classes."
    def test1(self):

        c = canvas.Canvas(fn,pagesize=letter)
        #Page 1
        c.setFont("Courier", 10)
        markPage(c)

        c.bookmarkPage("P1")
        c.addOutlineEntry("Page 1","P1")

        #Note : XYZ Left is ignored because at this zoom the whole page fits the screen
        c.bookmarkPage("P1_XYZ",fit="XYZ",top=7*inch,left=3*inch,zoom=0.5)
        c.addOutlineEntry("Page 1 XYZ #1 (top=7,left=3,zoom=0.5)","P1_XYZ",level=1)

        c.bookmarkPage("P1_XYZ2",fit="XYZ",top=7*inch,left=3*inch,zoom=5)
        c.addOutlineEntry("Page 1 XYZ #2 (top=7,left=3,zoom=5)","P1_XYZ2",level=1)

        c.bookmarkPage("P1_FIT",fit="Fit")
        c.addOutlineEntry("Page 1 Fit","P1_FIT",level=1)

        c.bookmarkPage("P1_FITH",fit="FitH",top=2*inch)
        c.addOutlineEntry("Page 1 FitH (top = 2 inch)","P1_FITH",level=1)

        c.bookmarkPage("P1_FITV",fit="FitV",left=3*inch)
        c.addOutlineEntry("Page 1 FitV (left = 3 inch)","P1_FITV",level=1)

        c.bookmarkPage("P1_FITR",fit="FitR",left=1*inch,bottom=2*inch,right=5*inch,top=6*inch)
        c.addOutlineEntry("Page 1 FitR (left=1,bottom=2,right=5,top=6)","P1_FITR",level=1)

        c.bookmarkPage("P1_FORWARD")
        c.addOutlineEntry("Forward References","P1_FORWARD",level=2)
        c.addOutlineEntry("Page 3 XYZ (top=7,left=3,zoom=0)","P3_XYZ",level=3)


        #Create link to FitR on page 3
        c.saveState()
        c.setFont("Courier", 14)
        c.setFillColor(colors.blue)
        c.drawString(inch+20,inch+20,"Click to jump to the meaning of life")
        c.linkAbsolute("","MOL",(inch+10,inch+10,6*inch,2*inch))
        c.restoreState()

        #Create linkAbsolute to page 2
        c.saveState()
        c.setFont("Courier", 14)
        c.setFillColor(colors.green)
        c.drawString(4*inch,4*inch,"Jump to 2.5 inch position on page 2")
        c.linkAbsolute("","HYPER_1",(3.75*inch,3.75*inch,8.25*inch,4.25*inch))
        c.restoreState()


        c.showPage()

        #Page 2
        c.setFont("Helvetica", 10)
        markPage(c)

        c.bookmarkPage("P2")
        c.addOutlineEntry("Page 2","P2")

        #Note : This time left will be at 3*inch because the zoom makes the page to big to fit
        c.bookmarkPage("P2_XYZ",fit="XYZ",top=7*inch,left=3*inch,zoom=2)
        c.addOutlineEntry("Page 2 XYZ (top=7,left=3,zoom=2.0)","P2_XYZ",level=1)

        c.bookmarkPage("P2_FIT",fit="Fit")
        c.addOutlineEntry("Page 2 Fit","P2_FIT",level=1)

        c.bookmarkPage("P2_FITH",fit="FitH",top=2*inch)
        c.addOutlineEntry("Page 2 FitH (top = 2 inch)","P2_FITH",level=1)

        c.bookmarkPage("P2_FITV",fit="FitV",left=10*inch)
        c.addOutlineEntry("Page 2 FitV (left = 10 inch)","P2_FITV",level=1)

        c.bookmarkPage("P2_FITR",fit="FitR",left=1*inch,bottom=2*inch,right=5*inch,top=6*inch)
        c.addOutlineEntry("Page 2 FitR (left=1,bottom=2,right=5,top=6)","P2_FITR",level=1)

        c.bookmarkPage("P2_FORWARD")
        c.addOutlineEntry("Forward References","P2_FORWARD",level=2)
        c.addOutlineEntry("Page 3 XYZ (top=7,left=3,zoom=0)","P3_XYZ",level=3)
        c.bookmarkPage("P2_BACKWARD")
        c.addOutlineEntry("Backward References","P2_BACKWARD",level=2)
        c.addOutlineEntry("Page 1 Fit","P1_FIT",level=3)
        c.addOutlineEntry("Page 1 FitR (left=1,bottom=2,right=5,top=6)","P1_FITR",level=3)

        #Horizontal absolute test from page 1. Note that because of the page size used on page 3 all this will do
        #is put the view centered on the bookmark. If you want to see it "up close and personal" change page3 to be
        #the same page size as the other pages.
        c.saveState()
        c.setFont("Courier", 14)
        c.setFillColor(colors.green)
        c.drawString(2.5*inch,2.5*inch,"This line is hyperlinked from page 1")
    #    c.bookmarkHorizontalAbsolute("HYPER_1",3*inch) #slightly higher than the text otherwise text is of screen above.
        c.bookmarkPage("HYPER_1",fit="XYZ",top=2.5*inch,bottom=2*inch)
        c.restoreState()

        #

        c.showPage()

        #Page 3
        c.setFont("Times-Roman", 10)
        #Turn the page on its size and make it 2* the normal "width" in order to have something to test FitV against.
        c.setPageSize((2*letter[1],letter[0]))
        markPage(c,height=letter[0],width=2*letter[1])

        c.bookmarkPage("P3")
        c.addOutlineEntry("Page 3 (Double-wide landscape page)","P3")

        #Note : XYZ with no zoom (set it to something first
        c.bookmarkPage("P3_XYZ",fit="XYZ",top=7*inch,left=3*inch,zoom=0)
        c.addOutlineEntry("Page 3 XYZ (top=7,left=3,zoom=0)","P3_XYZ",level=1)

        #FitV works here because the page is so wide it can"t all fit on the page
        c.bookmarkPage("P3_FITV",fit="FitV",left=10*inch)
        c.addOutlineEntry("Page 3 FitV (left = 10 inch)","P3_FITV",level=1)


        c.bookmarkPage("P3_BACKWARD")
        c.addOutlineEntry("Backward References","P3_BACKWARD",level=2)
        c.addOutlineEntry("Page 1 XYZ #1 (top=7,left=3,zoom=0.5)","P1_XYZ",level=3)
        c.addOutlineEntry("Page 1 XYZ #2 (top=7,left=3,zoom=5)","P1_XYZ2",level=3)
        c.addOutlineEntry("Page 2 FitV (left = 10 inch)","P2_FITV",level=3)

        #Add link from page 1
        c.saveState()
        c.setFont("Courier", 40)
        c.setFillColor(colors.green)
        c.drawString(5*inch,6*inch,"42")
        c.bookmarkPage("MOL",fit="FitR",left=4*inch,top=7*inch,bottom=4*inch,right=6*inch)




        c.showOutline()
        c.save()



def makeSuite():
    return makeSuiteForClasses(LinkTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    print "wrote", fn
    printLocation()
