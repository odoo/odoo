#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
import reportlab
reportlab._rl_testing=True
del reportlab
__version__='4.0.1'
__doc__="""Provides support for the test suite.

The test suite as a whole, and individual tests, need to share
certain support functions.  We have to put these in here so they
can always be imported, and so that individual tests need to import
nothing more than "reportlab.whatever..."
"""

import sys, os, fnmatch, re, functools
from configparser import ConfigParser
import unittest
from reportlab.lib.utils import isCompactDistro, __rl_loader__, rl_isdir, asUnicode

def haveRenderPM():
    from reportlab.graphics.renderPM import _getPMBackend, RenderPMError
    try:
        return _getPMBackend()
    except RenderPMError:
        return False

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

_OUTDIR = None
RL_HOME = None
testsFolder = None
def setOutDir(name):
    """Is it a writable file system distro being invoked within
    test directory?  If so, can write test output here.  If not,
    it had better go in a temp directory.  Only do this once per
    process"""
    global _OUTDIR, RL_HOME, testsFolder
    if _OUTDIR: return _OUTDIR
    D = [d[9:] for d in sys.argv if d.startswith('--outdir=')]
    if not D:
        D = os.environ.get('RL_TEST_OUTDIR','')
        if D: D=[D]
    if D:
        _OUTDIR = D[-1]
        try:
            os.makedirs(_OUTDIR)
        except:
            pass
        for d in D:
            if d in sys.argv:
                sys.argv.remove(d)
    else:
        assert name=='__main__',"setOutDir should only be called in the main script"
        scriptDir=os.path.dirname(sys.argv[0])
        if not scriptDir: scriptDir=os.getcwd()
        _OUTDIR = scriptDir

    if not isWritable(_OUTDIR):
        _OUTDIR = get_rl_tempdir('reportlab_test')

    import reportlab
    RL_HOME=reportlab.__path__[0]
    if not os.path.isabs(RL_HOME): RL_HOME=os.path.normpath(os.path.abspath(RL_HOME))
    topDir = os.path.dirname(RL_HOME)
    testsFolder = os.path.join(topDir,'tests')
    if not os.path.isdir(testsFolder):
        testsFolder = os.path.join(os.path.dirname(topDir),'tests')
    if not os.path.isdir(testsFolder):
        if name=='__main__':
            scriptDir=os.path.dirname(sys.argv[0])
            if not scriptDir: scriptDir=os.getcwd()
            testsFolder = os.path.abspath(scriptDir)
        else:
            testsFolder = None
    if testsFolder:
        sys.path.insert(0,os.path.dirname(testsFolder))
    return _OUTDIR

_mockumap = (
        None if os.environ.get('OFFLINE_MOCK','1')!='1' 
            else'http://www.reportlab.com/rsrc/encryption.gif',
        )
def mockUrlRead(name):
    if name in _mockumap:
        with open(os.path.join(testsFolder,os.path.basename(name)),'rb') as f:
            return f.read()
    else:
        from urllib.request import urlopen
        return urlopen(name).read()

def outputfile(fn):
    """This works out where to write test output.  If running
    code in a locked down file system, this will be a
    temp directory; otherwise, the output of 'test_foo.py' will
    normally be a file called 'test_foo.pdf', next door.
    """
    D = setOutDir(__name__)
    if fn: D = os.path.join(D,fn)
    return D

def printLocation(depth=1):
    if sys._getframe(depth).f_locals.get('__name__')=='__main__':
        outDir = outputfile('')
        if outDir!=_OUTDIR:
            print('Logs and output files written to folder "%s"' % outDir)

def makeSuiteForClasses(*classes,testMethodPrefix=None):
    "Return a test suite with tests loaded from provided classes."

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if testMethodPrefix:
        loader.testMethodPrefix = testMethodPrefix
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
            entry = line.split('/')[1]
            if entry:
                allEntries.append(join(folder, entry))

    return allEntries


# Still experimental class extending ConfigParser's behaviour.
class ExtConfigParser(ConfigParser):
    "A slightly extended version to return lists of strings."

    pat = re.compile(r'\s*\[.*\]\s*')

    def getstringlist(self, section, option):
        "Coerce option to a list of strings or return unchanged if that fails."

        value = ConfigParser.get(self, section, option)

        # This seems to allow for newlines inside values
        # of the config file, but be careful!!
        val = value.replace('\n', '')

        if self.pat.match(val):
            return eval(val,{__builtins__:None})
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
            if not isCompactDistro() or not __rl_loader__ or not rl_isdir(directory):
                raise ValueError('"%s" is not a directory' % directory)
            self.directory = directory[len(__rl_loader__.archive)+len(os.sep):]
            pfx = self.directory+os.sep
            n = len(pfx)
            self.files = list(map(lambda x, n=n: x[n:],list(filter(lambda x,pfx=pfx: x.startswith(pfx),list(__rl_loader__._files.keys())))))
            self.files.sort()
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
        GlobDirectoryWalker.__init__(self, directory, pattern)

        if ignore == None:
            ignore = []
        ip = [].append
        if isinstance(ignore,(tuple,list)):
            for p in ignore:
                ip(p)
        elif isinstance(ignore,str):
            ip(ignore)
        self.ignorePatterns = ([_.replace('/',os.sep) for _ in ip.__self__] if os.sep != '/'
                                else ip.__self__)

    def filterFiles(self, folder, files):
        "Filters all items from files matching patterns to ignore."

        fnm = fnmatch.fnmatch
        indicesToDelete = []
        for i,f in enumerate(files):
            for p in self.ignorePatterns:
                if fnm(f, p) or fnm(os.path.join(folder,f),p):
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
            for i in range(len(files)):
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
        self._initialPath = sys.path[:]
        self._initialWorkDir = os.getcwd()

    def tearDown(self):
        "Restore previous sys.path and working directory."
        sys.path = self._initialPath
        os.chdir(self._initialWorkDir)

class NearTestCase(unittest.TestCase):
    def assertNear(a,b,accuracy=1e-5):
        if isinstance(a,(float,int)):
            if abs(a-b)>accuracy:
                raise AssertionError("%s not near %s" % (a, b))
        else:
            for ae,be in zip(a,b):
                if abs(ae-be)>accuracy:
                    raise AssertionError("%s not near %s" % (a, b))
    assertNear = staticmethod(assertNear)

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
        global testsFolder
        scriptDir=self.scriptDir
        if not os.path.isabs(scriptDir):
            scriptDir=os.path.join(testsFolder,scriptDir)

        os.chdir(scriptDir)
        assert os.path.isfile(self.scriptName), "Script %s not found!" % self.scriptName
        if os.path.isfile(self.outFileName):
            os.remove(self.outFileName)

    def tearDown(self):
        os.chdir(self.cwd)

    def runTest(self):
        fmt = sys.platform=='win32' and '"%s" %s' or '%s %s'
        import subprocess
        out = subprocess.check_output((sys.executable,self.scriptName))
        #p = os.popen(fmt % (sys.executable,self.scriptName),'r')
        #out = p.read()
        if self.verbose:
            print(out)
        #status = p.close()
        assert os.path.isfile(self.outFileName), "File %s not created!" % self.outFileName

def equalStrings(a,b,enc='utf8'):
    return a==b if type(a)==type(b) else asUnicode(a,enc)==asUnicode(b,enc)

def eqCheck(r,x):
    if r!=x:
        print('Strings unequal\nexp: %s\ngot: %s' % (ascii(x),ascii(r)))

def rlextraNeeded():
    try:
        import rlextra
        return False
    except:
        return True

def rlSkipIf(cond,reason,__module__=None):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args,**kwds):
            if cond and os.environ.get('RL_indicateSkips','0')=='1':
                print(f'''
skipping {func.__module__ or __module__}.{func.__name__} {reason}''')
            return unittest.skipIf(cond,reason)(func)(*args,**kwds)
        return wrapper
    return inner

def rlSkipUnless(cond,reason,__module__=None):
    return rlSkipIf(not cond,reason,__module__=__module__)

def rlSkip(reason,__module__=None):
    return rlSkipIf(True,reason,__module__=__module__)
