"""Tests for the PythonPoint tool.
"""
import os, sys, string
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
import reportlab

class PythonPointTestCase(unittest.TestCase):
    "Some very crude tests on PythonPoint."
    def test0(self):
        "Test if pythonpoint.pdf can be created from pythonpoint.xml."

        join, dirname, isfile, abspath = os.path.join, os.path.dirname, os.path.isfile, os.path.abspath
        rlDir = abspath(dirname(reportlab.__file__))
        from reportlab.tools.pythonpoint import pythonpoint
        from reportlab.lib.utils import isCompactDistro, open_for_read
        ppDir = dirname(pythonpoint.__file__)
        xml = join(ppDir, 'demos', 'pythonpoint.xml')
        datafilename = 'pythonpoint.pdf'
        outDir = outputfile('')
        if isCompactDistro():
            cwd = None
            xml = open_for_read(xml)
        else:
            cwd = os.getcwd()
            os.chdir(join(ppDir, 'demos'))
        pdf = join(outDir, datafilename)
        if isfile(pdf): os.remove(pdf)
        pythonpoint.process(xml, outDir=outDir, verbose=0, datafilename=datafilename)
        if cwd: os.chdir(cwd)
        assert os.path.exists(pdf)

def makeSuite():
    return makeSuiteForClasses(PythonPointTestCase)

#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
