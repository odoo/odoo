#!/usr/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_docstrings.py

"""This is a test on a package level that find all modules,
classes, methods and functions that do not have a doc string
and lists them in individual log files.

Currently, methods with leading and trailing double underscores
are skipped.
"""

import os, sys, glob, string, re
from types import ModuleType, ClassType, MethodType, FunctionType

import reportlab
from reportlab.test import unittest
from reportlab.test.utils import SecureTestCase, GlobDirectoryWalker, outputfile, printLocation


RL_HOME = os.path.dirname(reportlab.__file__)

def getModuleObjects(folder, rootName, typ, pattern='*.py'):
    "Get a list of all objects defined *somewhere* in a package."

    # Define some abbreviations.
    find = string.find
    split = string.split
    replace = string.replace

    objects = []
    lookup = {}
    for file in GlobDirectoryWalker(folder, pattern):
        folder = os.path.dirname(file)

        if os.path.basename(file) == '__init__.py':
            continue

##        if os.path.exists(os.path.join(folder, '__init__.py')):
####            print 'skipping', os.path.join(folder, '__init__.py')
##            continue

        sys.path.insert(0, folder)
        cwd = os.getcwd()
        os.chdir(folder)

        modName = os.path.splitext(os.path.basename(file))[0]
        prefix = folder[find(folder, rootName):]
        prefix = replace(prefix, os.sep, '.')
        mName = prefix + '.' + modName

        try:
            module = __import__(mName)
        except ImportError:
            # Restore sys.path and working directory.
            os.chdir(cwd)
            del sys.path[0]
            continue

        # Get the 'real' (leaf) module
        # (__import__ loads only the top-level one).
        if find(mName, '.') != -1:
            for part in split(mName, '.')[1:]:
                module = getattr(module, part)

            # Find the objects in the module's content.
            modContentNames = dir(module)

            # Handle modules.
            if typ == ModuleType:
                if find(module.__name__, 'reportlab') > -1:
                    objects.append((mName, module))
                    continue

            for n in modContentNames:
                obj = eval(mName + '.' + n)
                # Handle functions and classes.
                if typ in (FunctionType, ClassType):
                    if type(obj) == typ and not lookup.has_key(obj):
                        if typ == ClassType:
                            if find(obj.__module__, rootName) != 0:
                                continue
                        objects.append((mName, obj))
                        lookup[obj] = 1
                # Handle methods.
                elif typ == MethodType:
                    if type(obj) == ClassType:
                        for m in dir(obj):
                            a = getattr(obj, m)
                            if type(a) == typ and not lookup.has_key(a):
                                if find(a.im_class.__module__, rootName) != 0:
                                    continue
                                cName = obj.__name__
                                objects.append((mName, a))
                                lookup[a] = 1

        # Restore sys.path and working directory.
        os.chdir(cwd)
        del sys.path[0]
    return objects

class DocstringTestCase(SecureTestCase):
    "Testing if objects in the ReportLab package have docstrings."

    def _writeLogFile(self, objType):
        "Write log file for different kind of documentable objects."

        cwd = os.getcwd()
        objects = getModuleObjects(RL_HOME, 'reportlab', objType)
        objects.sort()
        os.chdir(cwd)

        expl = {FunctionType:'functions',
                ClassType:'classes',
                MethodType:'methods',
                ModuleType:'modules'}[objType]

        path = outputfile("test_docstrings-%s.log" % expl)
        file = open(path, 'w')
        file.write('No doc strings found for the following %s below.\n\n' % expl)
        p = re.compile('__.+__')

        lines = []
        for name, obj in objects:
            if objType == MethodType:
                n = obj.__name__
                # Skip names with leading and trailing double underscores.
                if p.match(n):
                    continue

            if objType == FunctionType:
                if not obj.__doc__ or len(obj.__doc__) == 0:
                    lines.append("%s.%s\n" % (name, obj.__name__))
            else:
                if not obj.__doc__ or len(obj.__doc__) == 0:
                    if objType == ClassType:
                        lines.append("%s.%s\n" % (obj.__module__, obj.__name__))
                    elif objType == MethodType:
                        lines.append("%s.%s\n" % (obj.im_class, obj.__name__))
                    else:
                        lines.append("%s\n" % (obj.__name__))

        lines.sort()
        for line in lines:
            file.write(line)

        file.close()

    def test0(self):
        "Test if functions have a doc string."
        self._writeLogFile(FunctionType)

    def test1(self):
        "Test if classes have a doc string."
        self._writeLogFile(ClassType)

    def test2(self):
        "Test if methods have a doc string."
        self._writeLogFile(MethodType)

    def test3(self):
        "Test if modules have a doc string."
        self._writeLogFile(ModuleType)

def makeSuite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if sys.platform[:4] != 'java': suite.addTest(loader.loadTestsFromTestCase(DocstringTestCase))
    return suite

#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
