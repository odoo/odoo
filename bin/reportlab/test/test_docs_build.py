"""Tests that all manuals can be built.
"""


import os, sys

from reportlab.test import unittest
from reportlab.test.utils import SecureTestCase, printLocation


class ManualTestCase(SecureTestCase):
    "Runs all 3 manual-builders from the top."

    def test0(self):
        "Test if all manuals buildable from source."

        import reportlab
        rlFolder = os.path.dirname(reportlab.__file__)
        docsFolder = os.path.join(rlFolder, 'docs')
        os.chdir(docsFolder)

        if os.path.isfile('userguide.pdf'):
            os.remove('userguide.pdf')
        if os.path.isfile('graphguide.pdf'):
            os.remove('graphguide.pdf')
        if os.path.isfile('reference.pdf'):
            os.remove('reference.pdf')
        if os.path.isfile('graphics_reference.pdf'):
            os.remove('graphics_reference.pdf')

        os.system("%s genAll.py -s" % sys.executable)

        assert os.path.isfile('userguide.pdf'), 'genAll.py failed to generate userguide.pdf!'
        assert os.path.isfile('graphguide.pdf'), 'genAll.py failed to generate graphguide.pdf!'
        assert os.path.isfile('reference.pdf'), 'genAll.py failed to generate reference.pdf!'
        assert os.path.isfile('graphics_reference.pdf'), 'genAll.py failed to generate graphics_reference.pdf!'


def makeSuite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if sys.platform[:4] != 'java':
        suite.addTest(loader.loadTestsFromTestCase(ManualTestCase))

    return suite


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
