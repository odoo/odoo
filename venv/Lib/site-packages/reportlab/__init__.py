#Copyright ReportLab Europe Ltd. 2000-2021
#see license.txt for license details
__doc__="""The Reportlab PDF generation library."""
Version = "3.6.12"
__version__=Version
__date__='20220803'

import sys, os

__min_python_version__ = (3,7)
if sys.version_info< __min_python_version__:
    raise ImportError("""reportlab requires %s.%s+; other versions are unsupported.
If you want to try with other python versions edit line 10 of reportlab/__init__
to remove this error.""" % (__min_python_version__))

#define these early in reportlab's life
def cmp(a,b):
    return -1 if a<b else (1 if a>b else 0)

def _fake_import(fn,name):
    from importlib import machinery
    m = machinery.SourceFileLoader(name,fn)
    try:
        sys.modules[name] = m.load_module(name)
    except FileNotFoundError:
        raise ImportError('file %s not found' % ascii(fn))

#try to use dynamic modifications from
#reportlab.local_rl_mods.py
#reportlab_mods.py or ~/.reportlab_mods
try:
    import reportlab.local_rl_mods
except ImportError:
    pass

try:
    import reportlab_mods   #application specific modifications can be anywhere on python path
except ImportError:
    try:
        _fake_import(os.path.expanduser(os.path.join('~','.reportlab_mods')),'reportlab_mods')
    except (ImportError,KeyError,PermissionError):
        pass
