"""This executes tests defined outside the normal test suite.

See docstring for class ExternalTestCase for more information.
"""


import os, string, fnmatch, re, sys

import reportlab
from reportlab.test import unittest
from reportlab.test.utils import SecureTestCase, printLocation


RL_HOME = os.path.dirname(reportlab.__file__)
EXTRA_FILE = 'extra.txt'


class ExternalTestCase(SecureTestCase):
    """Test case starting cases external to the normal RL suite.

    This test case runs additional test cases defined in external
    modules which must also be using the unittest framework.
    These additional modules must be defined in a file named
    'extra.txt' which needs to be located in the reportlab/test
    folder and contains one path per line.

    The paths of these modules can contain stuff from the Unix
    world like '~', '.', '..' and '$HOME' and can have absolute
    or relative paths. If they are relative they start from the
    reportlab/test folder.

    This is a sample 'extra.txt' file:

        foo.py
        ./foo.py
        bar/foo.py
        ../foo.py
        /bar/foo.py
        ~/foo.py
        ~/bar/foo.py
        ~/../foo.py
        $HOME/bar/foo.py
    """

    def test0(self):
        "Execute external test cases."

        cwd = os.getcwd()

        # look for a file named 'extra.txt' in test directory,
        # exit if not found
        extraFilename = os.path.join(RL_HOME, 'test', EXTRA_FILE)
        if not os.path.exists(extraFilename):
            return

        # read module paths from file
        extraModulenames = open(extraFilename).readlines()
        extraModulenames = map(string.strip, extraModulenames)

        # expand pathnames as much as possible
        for f in extraModulenames:
            if f == '':
                continue
            if f[0] == '#':
                continue
            f = os.path.expanduser(f)
            f = os.path.expandvars(f)
            f = os.path.abspath(f)

            if os.path.exists(f):
                # look for a makeSuite function and execute it if present
                folder = os.path.abspath(os.path.dirname(f))
                modname = os.path.splitext(os.path.basename(f))[0]
                os.chdir(folder)
                sys.path.insert(0, folder)

                module = __import__(modname) # seems to fail sometimes...
                if 'makeSuite' in dir(module):
                    print "running", f
                    testSuite = module.makeSuite()
                    unittest.TextTestRunner().run(testSuite)
                os.chdir(cwd)
                sys.path = sys.path[1:]


def makeSuite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if sys.platform[:4] != 'java':
        suite.addTest(loader.loadTestsFromTestCase(ExternalTestCase))

    return suite


#noruntests
if __name__ == "__main__":
    if len(sys.argv) > 1:
        EXTRA_FILE = sys.argv[1]
        assert os.path.isfile(EXTRA_FILE), 'file %s not found!' % EXTRA_FILE
    # otherwise, extra.txt will be used
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
