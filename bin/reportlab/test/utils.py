"""Utilities for testing Python packages.
"""
import sys, os, string, fnmatch, copy, re
from ConfigParser import ConfigParser
from reportlab.test import unittest

# Helper functions.
def isWritable(D):
    try:
        fn = '00DELETE.ME'
        f = open(fn, 'w')
        f.write('test of writability - can be deleted')
        f.close()
        if os.path.isfile(fn):
            os.remove(fn)
            return 1
    except:
        return 0

_TEST_DIR_IS_WRITABLE = None  #not known yet
_OUTDIR = None
def canWriteTestOutputHere():
    """Is it a writable file system distro being invoked within
    test directory?  If so, can write test output here.  If not,
    it had better go in a temp directory.  Only do this once per
    process"""

    global _TEST_DIR_IS_WRITABLE, _OUTDIR
    if _TEST_DIR_IS_WRITABLE is not None:
        return _TEST_DIR_IS_WRITABLE

    D = [d[9:] for d in sys.argv if d.startswith('--outdir=')]
    if D:
        _OUTDIR = D[-1]
        try:
            os.makedirs(_OUTDIR)
        except:
            pass
        map(sys.argv.remove,D)
        _TEST_DIR_IS_WRITABLE = isWritable(_OUTDIR)
    else:
        from reportlab.lib.utils import isSourceDistro
        if isSourceDistro():
            curDir = os.getcwd()
            parentDir = os.path.dirname(curDir)
            if curDir.endswith('test') and parentDir.endswith('reportlab'):
                #we're probably being run within the test directory.
                #now check it's writeable.
                _TEST_DIR_IS_WRITABLE = isWritable(curDir)
                _OUTDIR = curDir
    return _TEST_DIR_IS_WRITABLE

def outputfile(fn):
    """This works out where to write test output.  If running
    code in a zip file or a locked down file system, this will be a
    temp directory; otherwise, the output of 'test_foo.py' will
    normally be a file called 'test_foo.pdf', next door.
    """
    if canWriteTestOutputHere():
        D = _OUTDIR
    else:
        from reportlab.lib.utils import isSourceDistro, get_rl_tempdir
        D = get_rl_tempdir('reportlab_test')
    if fn: D = os.path.join(D,fn)
    return D

def printLocation(depth=1):
    if sys._getframe(depth).f_locals.get('__name__')=='__main__':
        outDir = outputfile('')
        if outDir!=_OUTDIR:
            print 'Logs and output files written to folder "%s"' % outDir

def makeSuiteForClasses(*classes):
    "Return a test suite with tests loaded from provided classes."

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for C in classes:
        suite.addTest(loader.loadTestsFromTestCase(C))
    return suite

def getCVSEntries(folder, files=1, folders=0):
    """Returns a list of filenames as listed in the CVS/Entries file.

    'folder' is the folder that should contain the CVS subfolder.
    If there is no such subfolder an empty list is returned.
    'files' is a boolean; 1 and 0 means to return files or not.
    'folders' is a boolean; 1 and 0 means to return folders or not.
    """

    join = os.path.join
    split = string.split

    # If CVS subfolder doesn't exist return empty list.
    try:
        f = open(join(folder, 'CVS', 'Entries'))
    except IOError:
        return []

    # Return names of files and/or folders in CVS/Entries files.
    allEntries = []
    for line in f.readlines():
        if folders and line[0] == 'D' \
           or files and line[0] != 'D':
            entry = split(line, '/')[1]
            if entry:
                allEntries.append(join(folder, entry))

    return allEntries


# Still experimental class extending ConfigParser's behaviour.
class ExtConfigParser(ConfigParser):
    "A slightly extended version to return lists of strings."

    pat = re.compile('\s*\[.*\]\s*')

    def getstringlist(self, section, option):
        "Coerce option to a list of strings or return unchanged if that fails."

        value = apply(ConfigParser.get, (self, section, option))

        # This seems to allow for newlines inside values
        # of the config file, but be careful!!
        val = string.replace(value, '\n', '')

        if self.pat.match(val):
            return eval(val)
        else:
            return value


# This class as suggested by /F with an additional hook
# to be able to filter filenames.

class GlobDirectoryWalker:
    "A forward iterator that traverses files in a directory tree."

    def __init__(self, directory, pattern='*'):
        self.index = 0
        self.pattern = pattern
        directory.replace('/',os.sep)
        if os.path.isdir(directory):
            self.stack = [directory]
            self.files = []
        else:
            from reportlab.lib.utils import isCompactDistro, __loader__, rl_isdir
            if not isCompactDistro() or not __loader__ or not rl_isdir(directory):
                raise ValueError('"%s" is not a directory' % directory)
            self.directory = directory[len(__loader__.archive)+len(os.sep):]
            pfx = self.directory+os.sep
            n = len(pfx)
            self.files = map(lambda x, n=n: x[n:],filter(lambda x,pfx=pfx: x.startswith(pfx),__loader__._files.keys()))
            self.stack = []

    def __getitem__(self, index):
        while 1:
            try:
                file = self.files[self.index]
                self.index = self.index + 1
            except IndexError:
                # pop next directory from stack
                self.directory = self.stack.pop()
                self.files = os.listdir(self.directory)
                # now call the hook
                self.files = self.filterFiles(self.directory, self.files)
                self.index = 0
            else:
                # got a filename
                fullname = os.path.join(self.directory, file)
                if os.path.isdir(fullname) and not os.path.islink(fullname):
                    self.stack.append(fullname)
                if fnmatch.fnmatch(file, self.pattern):
                    return fullname

    def filterFiles(self, folder, files):
        "Filter hook, overwrite in subclasses as needed."

        return files


class RestrictedGlobDirectoryWalker(GlobDirectoryWalker):
    "An restricted directory tree iterator."

    def __init__(self, directory, pattern='*', ignore=None):
        apply(GlobDirectoryWalker.__init__, (self, directory, pattern))

        if ignore == None:
            ignore = []
        self.ignoredPatterns = []
        if type(ignore) == type([]):
            for p in ignore:
                self.ignoredPatterns.append(p)
        elif type(ignore) == type(''):
            self.ignoredPatterns.append(ignore)


    def filterFiles(self, folder, files):
        "Filters all items from files matching patterns to ignore."

        indicesToDelete = []
        for i in xrange(len(files)):
            f = files[i]
            for p in self.ignoredPatterns:
                if fnmatch.fnmatch(f, p):
                    indicesToDelete.append(i)
        indicesToDelete.reverse()
        for i in indicesToDelete:
            del files[i]

        return files


class CVSGlobDirectoryWalker(GlobDirectoryWalker):
    "An directory tree iterator that checks for CVS data."

    def filterFiles(self, folder, files):
        """Filters files not listed in CVS subfolder.

        This will look in the CVS subfolder of 'folder' for
        a file named 'Entries' and filter all elements from
        the 'files' list that are not listed in 'Entries'.
        """

        join = os.path.join
        cvsFiles = getCVSEntries(folder)
        if cvsFiles:
            indicesToDelete = []
            for i in xrange(len(files)):
                f = files[i]
                if join(folder, f) not in cvsFiles:
                    indicesToDelete.append(i)
            indicesToDelete.reverse()
            for i in indicesToDelete:
                del files[i]

        return files


# An experimental untested base class with additional 'security'.

class SecureTestCase(unittest.TestCase):
    """Secure testing base class with additional pre- and postconditions.

    We try to ensure that each test leaves the environment it has
    found unchanged after the test is performed, successful or not.

    Currently we restore sys.path and the working directory, but more
    of this could be added easily, like removing temporary files or
    similar things.

    Use this as a base class replacing unittest.TestCase and call
    these methods in subclassed versions before doing your own
    business!
    """

    def setUp(self):
        "Remember sys.path and current working directory."

        self._initialPath = copy.copy(sys.path)
        self._initialWorkDir = os.getcwd()


    def tearDown(self):
        "Restore previous sys.path and working directory."

        sys.path = self._initialPath
        os.chdir(self._initialWorkDir)


class ScriptThatMakesFileTest(unittest.TestCase):
    """Runs a Python script at OS level, expecting it to produce a file.

    It CDs to the working directory to run the script."""
    def __init__(self, scriptDir, scriptName, outFileName, verbose=0):
        self.scriptDir = scriptDir
        self.scriptName = scriptName
        self.outFileName = outFileName
        self.verbose = verbose
        # normally, each instance is told which method to run)
        unittest.TestCase.__init__(self)

    def setUp(self):

        self.cwd = os.getcwd()
        #change to reportlab directory first, so that
        #relative paths may be given to scriptdir
        import reportlab
        self.rl_dir = os.path.dirname(reportlab.__file__)
        self.fn = __file__
        os.chdir(self.rl_dir)

        os.chdir(self.scriptDir)
        assert os.path.isfile(self.scriptName), "Script %s not found!" % self.scriptName
        if os.path.isfile(self.outFileName):
            os.remove(self.outFileName)

    def tearDown(self):
        os.chdir(self.cwd)

    def runTest(self):
        fmt = sys.platform=='win32' and '"%s" %s' or '%s %s'
        p = os.popen(fmt % (sys.executable,self.scriptName),'r')
        out = p.read()
        if self.verbose:
            print out
        status = p.close()
        assert os.path.isfile(self.outFileName), "File %s not created!" % self.outFileName
