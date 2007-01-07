#!/usr/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_source_chars.py

"""This tests for things in source files.  Initially, absence of tabs :-)
"""

import os, sys, glob, string, re
from types import ModuleType, ClassType, MethodType, FunctionType

import reportlab
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, SecureTestCase, GlobDirectoryWalker, printLocation
from reportlab.lib.utils import open_and_read


class SourceTester(SecureTestCase):
    def setUp(self):
        SecureTestCase.setUp(self)
        try:
            fn = __file__
        except:
            fn = sys.argv[0]

        self.output = open(outputfile(os.path.splitext(os.path.basename(fn))[0]+'.txt'),'w')

    def checkFileForTabs(self, filename):
        txt = open_and_read(filename, 'r')
        chunks = string.split(txt, '\t')
        tabCount = len(chunks) - 1
        if tabCount:
            #raise Exception, "File %s contains %d tab characters!" % (filename, tabCount)
            self.output.write("file %s contains %d tab characters!\n" % (filename, tabCount))

    def checkFileForTrailingSpaces(self, filename):
        txt = open_and_read(filename, 'r')
        initSize = len(txt)
        badLines = 0
        badChars = 0
        for line in string.split(txt, '\n'):
            stripped = string.rstrip(line)
            spaces = len(line) - len(stripped)  # OK, so they might be trailing tabs, who cares?
            if spaces:
                badLines = badLines + 1
                badChars = badChars + spaces

        if badChars <> 0:
            self.output.write("file %s contains %d trailing spaces, or %0.2f%% wastage\n" % (filename, badChars, 100.0*badChars/initSize))

    def testFiles(self):
        topDir = os.path.dirname(reportlab.__file__)
        w = GlobDirectoryWalker(topDir, '*.py')
        for filename in w:
            self.checkFileForTabs(filename)
            self.checkFileForTrailingSpaces(filename)

def zapTrailingWhitespace(dirname):
    """Eliminates trailing spaces IN PLACE.  Use with extreme care
    and only after a backup or with version-controlled code."""
    assert os.path.isdir(dirname), "Directory not found!"
    print "This will eliminate all trailing spaces in py files under %s." % dirname
    ok = raw_input("Shall I proceed?  type YES > ")
    if ok <> 'YES':
        print 'aborted by user'
        return
    w = GlobDirectoryWalker(dirname, '*.py')
    for filename in w:
        # trim off final newline and detect real changes
        txt = open(filename, 'r').read()
        badChars = 0
        cleaned = []
        for line in string.split(txt, '\n'):
            stripped = string.rstrip(line)
            cleaned.append(stripped)
            spaces = len(line) - len(stripped)  # OK, so they might be trailing tabs, who cares?
            if spaces:
                badChars = badChars + spaces

        if badChars <> 0:
            open(filename, 'w').write(string.join(cleaned, '\n'))
            print "file %s contained %d trailing spaces, FIXED" % (filename, badChars)
    print 'done'

def makeSuite():
    return makeSuiteForClasses(SourceTester)


#noruntests
if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == 'zap' and os.path.isdir(sys.argv[2]):
        zapTrailingWhitespace(sys.argv[2])
    else:
        unittest.TextTestRunner().run(makeSuite())
        printLocation()
