#Copyright ReportLab Europe Ltd. 2000-2006
#see license.txt for license details
# $URI:$
__version__=''' $Id: rltempfile.py 2892 2006-05-19 14:16:02Z rgbecker $ '''
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
