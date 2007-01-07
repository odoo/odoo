#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/demos/odyssey/odyssey.py
__version__=''' $Id: odyssey.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
___doc__=''
#odyssey.py
#
#Demo/benchmark of PDFgen rendering Homer's Odyssey.



#results on my humble P266 with 64MB:
# Without page compression:
# 239 pages in 3.76 seconds = 77 pages per second

# With textOut rather than textLine, i.e. computing width
# of every word as we would for wrapping:
# 239 pages in 10.83 seconds = 22 pages per second

# With page compression and textLine():
# 239 pages in 39.39 seconds = 6 pages per second

from reportlab.pdfgen import canvas
import time, os, sys

#find out what platform we are on and whether accelerator is
#present, in order to print this as part of benchmark info.
try:
    import _rl_accel
    ACCEL = 1
except ImportError:
    ACCEL = 0




from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import A4

#precalculate some basics
top_margin = A4[1] - inch
bottom_margin = inch
left_margin = inch
right_margin = A4[0] - inch
frame_width = right_margin - left_margin


def drawPageFrame(canv):
    canv.line(left_margin, top_margin, right_margin, top_margin)
    canv.setFont('Times-Italic',12)
    canv.drawString(left_margin, top_margin + 2, "Homer's Odyssey")
    canv.line(left_margin, top_margin, right_margin, top_margin)


    canv.line(left_margin, bottom_margin, right_margin, bottom_margin)
    canv.drawCentredString(0.5*A4[0], 0.5 * inch,
               "Page %d" % canv.getPageNumber())



def run(verbose=1):
    if sys.platform[0:4] == 'java':
        impl = 'Jython'
    else:
        impl = 'Python'
    verStr = '%d.%d' % (sys.version_info[0:2])
    if ACCEL:
        accelStr = 'with _rl_accel'
    else:
        accelStr = 'without _rl_accel'
    print 'Benchmark of %s %s %s' % (impl, verStr, accelStr)

    started = time.time()
    canv = canvas.Canvas('odyssey.pdf', invariant=1)
    canv.setPageCompression(1)
    drawPageFrame(canv)

    #do some title page stuff
    canv.setFont("Times-Bold", 36)
    canv.drawCentredString(0.5 * A4[0], 7 * inch, "Homer's Odyssey")

    canv.setFont("Times-Bold", 18)
    canv.drawCentredString(0.5 * A4[0], 5 * inch, "Translated by Samuel Burton")

    canv.setFont("Times-Bold", 12)
    tx = canv.beginText(left_margin, 3 * inch)
    tx.textLine("This is a demo-cum-benchmark for PDFgen.  It renders the complete text of Homer's Odyssey")
    tx.textLine("from a text file.  On my humble P266, it does 77 pages per secondwhile creating a 238 page")
    tx.textLine("document.  If it is asked to computer text metrics, measuring the width of each word as ")
    tx.textLine("one would for paragraph wrapping, it still manages 22 pages per second.")
    tx.textLine("")
    tx.textLine("Andy Robinson, Robinson Analytics Ltd.")
    canv.drawText(tx)

    canv.showPage()
    #on with the text...
    drawPageFrame(canv)

    canv.setFont('Times-Roman', 12)
    tx = canv.beginText(left_margin, top_margin - 0.5*inch)

    for fn in ('odyssey.full.txt','odyssey.txt'):
        if os.path.isfile(fn):
            break

    data = open(fn,'r').readlines()
    for line in data:
        #this just does it the fast way...
        tx.textLine(line)
        #this forces it to do text metrics, which would be the slow
        #part if we were wrappng paragraphs.
        #canv.textOut(line)
        #canv.textLine('')

        #page breaking
        y = tx.getY()   #get y coordinate
        if y < bottom_margin + 0.5*inch:
            canv.drawText(tx)
            canv.showPage()
            drawPageFrame(canv)
            canv.setFont('Times-Roman', 12)
            tx = canv.beginText(left_margin, top_margin - 0.5*inch)

            #page
            pg = canv.getPageNumber()
            if verbose and pg % 10 == 0:
                print 'formatted page %d' % canv.getPageNumber()

    if tx:
        canv.drawText(tx)
        canv.showPage()
        drawPageFrame(canv)

    if verbose:
        print 'about to write to disk...'

    canv.save()

    finished = time.time()
    elapsed = finished - started
    pages = canv.getPageNumber()-1
    speed =  pages / elapsed
    fileSize = os.stat('odyssey.pdf')[6] / 1024
    print '%d pages in %0.2f seconds = %0.2f pages per second, file size %d kb' % (
                pages, elapsed, speed, fileSize)
    import md5
    print 'file digest: %s' % md5.md5(open('odyssey.pdf','rb').read()).hexdigest()

if __name__=='__main__':
    quiet = ('-q' in sys.argv)
    run(verbose = not quiet)