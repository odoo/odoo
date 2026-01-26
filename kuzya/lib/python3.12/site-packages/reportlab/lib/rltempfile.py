#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
# $URI:$
__version__='3.3.0'
__doc__='''Helper for the test suite - determines where to write output.

When our test suite runs as source, a script "test_foo.py" will typically
create "test_foo.pdf" alongside it.  But if you are testing a package of
compiled code inside a zip archive, this won't work.  This determines
where to write test suite output, creating a subdirectory of /tmp/ or
whatever if needed.

'''
_rl_tempdir=None
__all__ = ('get_rl_tempdir', 'get_rl_tempdir')
import os, tempfile
def _rl_getuid():
    if hasattr(os,'getuid'):
        return os.getuid()
    else:
        return ''

def get_rl_tempdir(*subdirs):
    global _rl_tempdir
    if _rl_tempdir is None:
        _rl_tempdir = os.path.join(tempfile.gettempdir(),'ReportLab_tmp%s' % str(_rl_getuid()))
    d = _rl_tempdir
    if subdirs: d = os.path.join(*((d,)+subdirs))
    try:
        os.makedirs(d)
    except:
        pass
    return d

def get_rl_tempfile(fn=None):
    if not fn:
        fn = tempfile.mktemp()
    return os.path.join(get_rl_tempdir(),fn)
