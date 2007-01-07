"""Tests for reportlab.lib.utils
"""
import os
import reportlab
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation
from reportlab.lib import colors
from reportlab.lib.utils import recursiveImport, recursiveGetAttr, recursiveSetAttr, rl_isfile, \
                                isCompactDistro

class ImporterTestCase(unittest.TestCase):
    "Test import utilities"
    count = 0

    def setUp(self):
        from time import time
        from reportlab.lib.utils import get_rl_tempdir
        s = `int(time())` + `self.count`
        self.__class__.count += 1
        self._tempdir = get_rl_tempdir('reportlab_test','tmp_%s' % s)
        _testmodulename = os.path.join(self._tempdir,'test_module_%s.py' % s)
        f = open(_testmodulename,'w')
        f.write('__all__=[]\n')
        f.close()
        self._testmodulename = os.path.splitext(os.path.basename(_testmodulename))[0]

    def tearDown(self):
        from shutil import rmtree
        rmtree(self._tempdir,1)

    def test1(self):
        "try stuff known to be in the path"
        m1 = recursiveImport('reportlab.pdfgen.canvas')
        import reportlab.pdfgen.canvas
        assert m1 == reportlab.pdfgen.canvas

    def test2(self):
        "try under a well known directory NOT on the path"
        D = os.path.join(os.path.dirname(reportlab.__file__), 'tools','pythonpoint')
        fn = os.path.join(D,'stdparser.py')
        if rl_isfile(fn) or rl_isfile(fn+'c') or rl_isfile(fn+'o'):
            m1 = recursiveImport('stdparser', baseDir=D)

    def test3(self):
        "ensure CWD is on the path"
        try:
            cwd = os.getcwd()
            os.chdir(self._tempdir)
            m1 = recursiveImport(self._testmodulename)
        finally:
            os.chdir(cwd)

    def test4(self):
        "ensure noCWD removes current dir from path"
        try:
            cwd = os.getcwd()
            os.chdir(self._tempdir)
            import sys
            try:
                del sys.modules[self._testmodulename]
            except KeyError:
                pass
            self.assertRaises(ImportError,
                              recursiveImport,
                              self._testmodulename,
                              noCWD=1)
        finally:
            os.chdir(cwd)

    def test5(self):
        "recursive attribute setting/getting on modules"
        import reportlab.lib.units
        inch = recursiveGetAttr(reportlab, 'lib.units.inch')
        assert inch == 72

        recursiveSetAttr(reportlab, 'lib.units.cubit', 18*inch)
        cubit = recursiveGetAttr(reportlab, 'lib.units.cubit')
        assert cubit == 18*inch

    def test6(self):
        "recursive attribute setting/getting on drawings"
        from reportlab.graphics.charts.barcharts import sampleH1
        drawing = sampleH1()
        recursiveSetAttr(drawing, 'barchart.valueAxis.valueMax', 72)
        theMax = recursiveGetAttr(drawing, 'barchart.valueAxis.valueMax')
        assert theMax == 72

    def test7(self):
        "test open and read of a simple relative file"
        from reportlab.lib.utils import open_and_read
        b = open_and_read('../docs/images/Edit_Prefs.gif')

    def test8(self):
        "test open and read of a relative file: URL"
        from reportlab.lib.utils import open_and_read
        b = open_and_read('file:../docs/images/Edit_Prefs.gif')

    def test9(self):
        "test open and read of an http: URL"
        from reportlab.lib.utils import open_and_read
        b = open_and_read('http://www.reportlab.com/rsrc/encryption.gif')

    def test10(self):
        "test open and read of a simple relative file"
        from reportlab.lib.utils import open_and_read, getStringIO
        b = getStringIO(open_and_read('../docs/images/Edit_Prefs.gif'))
        b = open_and_read(b)

def makeSuite():
    return makeSuiteForClasses(ImporterTestCase)


if __name__ == "__main__": #noruntests
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
