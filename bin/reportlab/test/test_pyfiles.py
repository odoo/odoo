#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_pyfiles.py
"""Tests performed on all Python source files of the ReportLab distribution.
"""


import os, sys, string, fnmatch, re

import reportlab
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, SecureTestCase, GlobDirectoryWalker, outputfile, printLocation
from reportlab.lib.utils import open_and_read, open_and_readlines

RL_HOME = os.path.dirname(reportlab.__file__)


# Helper function and class.

def unique(seq):
    "Remove elements from a list that occur more than once."

    # Return input if it has less than 2 elements.
    if len(seq) < 2:
        return seq

    # Make a sorted copy of the input sequence.
    seq2 = seq[:]
    if type(seq2) == type(''):
        seq2 = map(None, seq2)
    seq2.sort()

    # Remove adjacent elements if they are identical.
    i = 0
    while i < len(seq2)-1:
        elem = seq2[i]
        try:
            while elem == seq2[i+1]:
                del seq2[i+1]
        except IndexError:
            pass
        i = i + 1

    # Try to return something of the same type as the input.
    if type(seq) == type(''):
        return string.join(seq2, '')
    else:
        return seq2

class SelfTestCase(unittest.TestCase):
    "Test unique() function."

    def testUnique(self):
        "Test unique() function."

        cases = [([], []),
                 ([0], [0]),
                 ([0, 1, 2], [0, 1, 2]),
                 ([2, 1, 0], [0, 1, 2]),
                 ([0, 0, 1, 1, 2, 2, 3, 3], [0, 1, 2, 3]),
                 ('abcabcabc', 'abc')
                 ]

        msg = "Failed: unique(%s) returns %s instead of %s."
        for sequence, expectedOutput in cases:
            output = unique(sequence)
            args = (sequence, output, expectedOutput)
            assert output == expectedOutput, msg % args


class AsciiFileTestCase(unittest.TestCase):
    "Test if Python files are pure ASCII ones."

    def testAscii(self):
        "Test if Python files are pure ASCII ones."

        RL_HOME = os.path.dirname(reportlab.__file__)
        allPyFiles = GlobDirectoryWalker(RL_HOME, '*.py')

        for path in allPyFiles:
            fileContent = open_and_read(path,'r')
            nonAscii = filter(lambda c: ord(c)>127, fileContent)
            nonAscii = unique(nonAscii)

            truncPath = path[string.find(path, 'reportlab'):]
            args = (truncPath, repr(map(ord, nonAscii)))
            msg = "File %s contains characters: %s." % args
##            if nonAscii:
##                print msg
            assert nonAscii == '', msg


class FilenameTestCase(unittest.TestCase):
    "Test if Python files contain trailing digits."

    def testTrailingDigits(self):
        "Test if Python files contain trailing digits."

        allPyFiles = GlobDirectoryWalker(RL_HOME, '*.py')

        for path in allPyFiles:
            #hack - exclude barcode extensions from this test
            if string.find(path, 'barcode'):
                pass
            else:
                basename = os.path.splitext(path)[0]
                truncPath = path[string.find(path, 'reportlab'):]
                msg = "Filename %s contains trailing digits." % truncPath
                assert basename[-1] not in string.digits, msg

    ##            if basename[-1] in string.digits:
    ##                print truncPath


class FirstLineTestCase(SecureTestCase):
    "Testing if objects in the ReportLab package have docstrings."

    def findSuspiciousModules(self, folder, rootName):
        "Get all modul paths with non-Unix-like first line."

        firstLinePat = re.compile('^#!.*python.*')

        paths = []
        for file in GlobDirectoryWalker(folder, '*.py'):
            if os.path.basename(file) == '__init__.py':
                continue
            firstLine = open_and_readlines(file)[0]
            if not firstLinePat.match(firstLine):
                paths.append(file)

        return paths

    def test1(self):
        "Test if all Python files have a Unix-like first line."

        path = outputfile("test_firstline.log")
        file = open(path, 'w')
        file.write('No Unix-like first line found in the files below.\n\n')

        paths = self.findSuspiciousModules(RL_HOME, 'reportlab')
        paths.sort()

        for p in paths:
            file.write("%s\n" % p)

        file.close()

def makeSuite():
    suite = makeSuiteForClasses(SelfTestCase, AsciiFileTestCase, FilenameTestCase)
    if sys.platform[:4] != 'java':
        loader = unittest.TestLoader()
        suite.addTest(loader.loadTestsFromTestCase(FirstLineTestCase))
    return suite

#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
