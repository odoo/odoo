#!/usr/pkg/bin/python

import os, sys, time

from reportlab.graphics.barcode.common import *
from reportlab.graphics.barcode.code39 import *
from reportlab.graphics.barcode.code93 import *
from reportlab.graphics.barcode.code128 import *
from reportlab.graphics.barcode.usps import *


from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.platypus import Spacer, SimpleDocTemplate, Table, TableStyle, Preformatted, PageBreak
from reportlab.lib.units import inch, cm
from reportlab.lib import colors

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.frames import Frame
from reportlab.platypus.flowables import XBox, KeepTogether
from reportlab.graphics.shapes import Drawing

from reportlab.graphics.barcode import getCodes, getCodeNames, createBarcodeDrawing
def run():
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleH = styles['Heading1']
    story = []

    #for codeNames in code
    story.append(Paragraph('I2of5', styleN))
    story.append(I2of5(1234, barWidth = inch*0.02, checksum=0))
    story.append(Paragraph('MSI', styleN))
    story.append(MSI(1234))
    story.append(Paragraph('Codabar', styleN))
    story.append(Codabar("A012345B", barWidth = inch*0.02))
    story.append(Paragraph('Code 11', styleN))
    story.append(Code11("01234545634563"))
    story.append(Paragraph('Code 39', styleN))
    story.append(Standard39("A012345B%R"))
    story.append(Paragraph('Extended Code 39', styleN))
    story.append(Extended39("A012345B}"))
    story.append(Paragraph('Code93', styleN))
    story.append(Standard93("CODE 93"))
    story.append(Paragraph('Extended Code93', styleN))
    story.append(Extended93("L@@K! Code 93 :-)")) #, barWidth=0.005 * inch))
    story.append(Paragraph('Code 128', styleN))
    c=Code128("AB-12345678") #, barWidth=0.005 * inch)
    #print 'WIDTH =', (c.width / inch), 'barWidth =', (c.barWidth / inch)
    #print 'LQ =', (c.lquiet / inch), 'RQ =', (c.rquiet / inch)
    story.append(c)
    story.append(Paragraph('USPS FIM', styleN))
    story.append(FIM("A"))
    story.append(Paragraph('USPS POSTNET', styleN))
    story.append(POSTNET('78247-1043'))

    from reportlab.graphics.barcode import createBarcodeDrawing
    story.append(Paragraph('EAN13', styleN))
    bcd = createBarcodeDrawing('EAN13', value='123456789012')
    story.append(bcd)
    story.append(Paragraph('EAN8', styleN))
    bcd = createBarcodeDrawing('EAN8', value='1234567')
    story.append(bcd)

    story.append(Paragraph('Label Size', styleN))
    story.append(XBox((2.0 + 5.0/8.0)*inch, 1 * inch, '1x2-5/8"'))
    story.append(Paragraph('Label Size', styleN))
    story.append(XBox((1.75)*inch, .5 * inch, '1/2x1-3/4"'))
    c = Canvas('out.pdf')
    f = Frame(inch, inch, 6*inch, 9*inch, showBoundary=1)
    f.addFromList(story, c)
    c.save()
    print 'saved out.pdf'

def fullTest(fileName="test_full.pdf"):
    """Creates large-ish test document with a variety of parameters"""

    story = []

    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleH = styles['Heading1']
    styleH2 = styles['Heading2']
    story = []

    story.append(Paragraph('ReportLab Barcode Test Suite - full output', styleH))
    story.append(Paragraph('Generated on %s' % time.ctime(time.time()), styleN))

    story.append(Paragraph('', styleN))
    story.append(Paragraph('Repository information for this build:', styleN))
    #see if we can figure out where it was built, if we're running in source
    if os.path.split(os.getcwd())[-1] == 'barcode' and os.path.isdir('.svn'):
        #runnning in a filesystem svn copy
        infoLines = os.popen('svn info').read()
        story.append(Preformatted(infoLines, styles["Code"]))
        
    story.append(Paragraph('About this document', styleH2))
    story.append(Paragraph('History and Status', styleH2))

    story.append(Paragraph("""
        This is the test suite and docoumentation for the ReportLab open source barcode API,
        being re-released as part of the forthcoming ReportLab 2.0 release.
        """, styleN))

    story.append(Paragraph("""
        Several years ago Ty Sarna contributed a barcode module to the ReportLab community.
        Several of the codes were used by him in hiw work and to the best of our knowledge
        this was correct.  These were written as flowable objects and were available in PDFs,
        but not in our graphics framework.  However, we had no knowledge of barcodes ourselves
        and did not advertise or extend the package.
        """, styleN))

    story.append(Paragraph("""
        We "wrapped" the barcodes to be usable within our graphics framework; they are now available
        as Drawing objects which can be rendered to EPS files or bitmaps.  For the last 2 years this
        has been available in our Diagra and Report Markup Language products.  However, we did not
        charge separately and use was on an "as is" basis.
        """, styleN))

    story.append(Paragraph("""
        A major licensee of our technology has kindly agreed to part-fund proper productisation
        of this code on an open source basis in Q1 2006.  This has involved addition of EAN codes
        as well as a proper testing program.  Henceforth we intend to publicise the code more widely,
        gather feedback, accept contributions of code and treat it as "supported".  
        """, styleN))

    story.append(Paragraph("""
        This involved making available both downloads and testing resources.  This PDF document
        is the output of the current test suite.  It contains codes you can scan (if you use a nice sharp
        laser printer!), and will be extended over coming weeks to include usage examples and notes on
        each barcode and how widely tested they are.  This is being done through documentation strings in
        the barcode objects themselves so should always be up to date.
        """, styleN))

    story.append(Paragraph('Usage examples', styleH2))
    story.append(Paragraph("""
        To be completed
        """, styleN))

    story.append(Paragraph('The codes', styleH2))
    story.append(Paragraph("""
        Below we show a scannable code from each barcode, with and without human-readable text.
        These are magnified about 2x from the natural size done by the original author to aid
        inspection.  This will be expanded to include several test cases per code, and to add
        explanations of checksums.  Be aware that (a) if you enter numeric codes which are too
        short they may be prefixed for you (e.g. "123" for an 8-digit code becomes "00000123"),
        and that the scanned results and readable text will generally include extra checksums
        at the end.
        """, styleN))

    codeNames = getCodeNames()
    from reportlab.lib.utils import flatten
    width = [float(x[8:]) for x in sys.argv if x.startswith('--width=')]
    height = [float(x[9:]) for x in sys.argv if x.startswith('--height=')]
    isoScale = [int(x[11:]) for x in sys.argv if x.startswith('--isoscale=')]
    options = {}
    if width: options['width'] = width[0]
    if height: options['height'] = height[0]
    if isoScale: options['isoScale'] = isoScale[0]
    scales = [x[8:].split(',') for x in sys.argv if x.startswith('--scale=')]
    scales = map(float,scales and flatten(scales) or [1])
    scales = map(float,scales and flatten(scales) or [1])
    for scale in scales:
        story.append(PageBreak())
        story.append(Paragraph('Scale = %.1f'%scale, styleH2))
        story.append(Spacer(36, 12))
        for codeName in codeNames:
            s = [Paragraph('Code: ' + codeName, styleH2)]
            for hr in (0,1):
                s.append(Spacer(36, 12))
                dr = createBarcodeDrawing(codeName, humanReadable=hr,**options)
                dr.renderScale = scale
                s.append(dr)
                s.append(Spacer(36, 12))
            s.append(Paragraph('Barcode should say: ' + dr._bc.value, styleN))
            story.append(KeepTogether(s))

    SimpleDocTemplate(fileName).build(story)
    print 'created', fileName

if __name__=='__main__':
    run()
    fullTest()
