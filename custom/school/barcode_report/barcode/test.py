# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from . import I2of5, MSI, Codabar, Code11
from . import Standard39, Extended39
from . import Standard93, Extended93
from . import Code128
from . import FIM, POSTNET, inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Frame
from reportlab.platypus.flowables import XBox


def run():
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    story = []
    story.append(Paragraph('I2of5', styleN))
    story.append(I2of5(1234, xdim=inch * 0.02, checksum=0))
    story.append(Paragraph('MSI', styleN))
    story.append(MSI(1234, xdim=inch * 0.02))
    story.append(Paragraph('Codabar', styleN))
    story.append(Codabar("A012345B", xdim=inch * 0.02))
    story.append(Paragraph('Code 11', styleN))
    story.append(Code11("01234545634563"))
    story.append(Paragraph('Code 39', styleN))
    story.append(Standard39("A012345B%R"))
    story.append(Paragraph('Extended Code 39', styleN))
    story.append(Extended39("A012345B}"))
    story.append(Paragraph('Code93', styleN))
    story.append(Standard93("CODE 93"))
    story.append(Paragraph('Extended Code93', styleN))
    story.append(Extended93("L@@K! Code 93 :-)"))
    story.append(Paragraph('Code 128', styleN))
    c = Code128("AB-12345678")
    story.append(c)
    story.append(Paragraph('USPS FIM', styleN))
    story.append(FIM("A"))
    story.append(Paragraph('USPS POSTNET', styleN))
    story.append(POSTNET('78247-1043'))
    story.append(Paragraph('Label Size', styleN))
    story.append(XBox((2.0 + 5.0 / 8.0) * inch, 1 * inch, '1x2-5/8"'))
    story.append(Paragraph('Label Size', styleN))
    story.append(XBox((1.75) * inch, .5 * inch, '1/2x1-3/4"'))
    c = Canvas('out.pdf')
    f = Frame(inch, inch, 6 * inch, 9 * inch, showBoundary=1)
    f.addFromList(story, c)
    c.save()


if __name__ == '__main__':
    run()
