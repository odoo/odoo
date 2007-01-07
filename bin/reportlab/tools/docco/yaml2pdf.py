#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/yaml2pdf.py
# yaml2pdf - turns stuff in Yet Another Markup Language
# into PDF documents.  Very crude - it assumes a
# doc template and stylesheet (hard coded for now)
# and basically cranks out paragraphs in each style
"""yaml2pdf.py - converts Yet Another Markup Language
to reasonable PDF documents.  This is ReportLab's
basic documentation tool.

Usage:
.  "yaml2pdf.py filename.ext" will create "filename.pdf"
"""

import sys
import os
import imp

import yaml
from rltemplate import RLDocTemplate
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import *
from reportlab.lib.pagesizes import A4
from reportlab.platypus import *
from reportlab.lib import colors
from reportlab.lib.units import inch


from stylesheet import getStyleSheet


def run(infilename, outfilename):
    p = yaml.Parser()
    results = p.parseFile(infilename)

    ss = getStyleSheet()

    #now make flowables from the results
    story = []
    for thingy in results:
        typ = thingy[0]
        if typ == 'Paragraph':
            (typ2, stylename, text) = thingy
            if stylename == 'bu':
                bulletText='\267'
            else:
                bulletText=None
            try:
                style = ss[stylename]
            except KeyError:
                print 'Paragraph style "%s" not found in stylesheet, using Normal instead' % stylename
                style = ss['Normal']
            story.append(Paragraph(text, style, bulletText=bulletText))
        elif typ == 'Preformatted':
            (typ2, stylename, text) = thingy
            try:
                style = ss[stylename]
            except KeyError:
                print 'Preformatted style "%s" not found in stylesheet, using Normal instead' % stylename
                style = ss['Normal']
            story.append(Preformatted(text, style, bulletText=bulletText))
        elif typ == 'Image':
            filename = thingy[1]
            img = Image(filename)
            story.append(img)
        elif typ == 'PageBreak':
            story.append(PageBreak())
        elif typ == 'VSpace':
            height = thingy[1]
            story.append(Spacer(0, height))
        elif typ == 'NextPageTemplate':
            story.append(NextPageTemplate(thingy[1]))
        elif typ == 'Custom':
            # go find it
            searchPath = [os.getcwd()+'\\']
            (typ2, moduleName, funcName) = thingy
            found = imp.find_module(moduleName, searchPath)
            assert found, "Custom object module %s not found" % moduleName
            (file, pathname, description) = found
            mod = imp.load_module(moduleName, file, pathname, description)

            #now get the function
            func = getattr(mod, funcName)
            story.append(func())

        else:
            print 'skipping',typ, 'for now'


    #print it
    doc = RLDocTemplate(outfilename, pagesize=A4)
    doc.build(story)

if __name__ == '__main__': #NORUNTESTS
    if len(sys.argv) == 2:
        infilename = sys.argv[1]
        outfilename = os.path.splitext(infilename)[0] + '.pdf'
        if os.path.isfile(infilename):
            run(infilename, outfilename)
        else:
            print 'File not found %s' % infilename
    else:
        print __doc__