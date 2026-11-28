'''module that aggregates config information'''
__all__=('_reset','register_reset')

def _defaults_init():
    '''
    create & return defaults for all reportlab settings from
    reportlab.rl_settings.py
    reportlab.local_rl_settings.py
    reportlab_settings.py or ~/.reportlab_settings

    latter values override earlier
    '''
    from reportlab.lib.utils import rl_exec
    import os

    _DEFAULTS={}
    rl_exec('from reportlab.rl_settings import *',_DEFAULTS)

    _overrides=_DEFAULTS.copy()
    try:
        rl_exec('from reportlab.local_rl_settings import *',_overrides)
        _DEFAULTS.update(_overrides)
    except ImportError:
        pass

    _overrides=_DEFAULTS.copy()
    try:
        rl_exec('from reportlab_settings import *',_overrides)
        _DEFAULTS.update(_overrides)
    except ImportError:
        _overrides=_DEFAULTS.copy()
        try:
            try:
                fn = os.path.expanduser(os.path.join('~','.reportlab_settings'))    #appengine fails with KeyError/ImportError (dev/live)
            except (KeyError, ImportError):
                fn = None
            if fn:
                with open(fn,'rb') as f:
                    rl_exec(f.read(),_overrides)
                _DEFAULTS.update(_overrides)
        except:
            pass
    return _DEFAULTS

_DEFAULTS=_defaults_init()

_SAVED = {}
sys_version=None

#this is used to set the options from
def _setOpt(name, value, conv=None):
    '''set a module level value from environ/default'''
    from os import environ
    ename = 'RL_'+name
    if ename in environ:
        value = environ[ename]
    if conv: value = conv(value)
    globals()[name] = value

def _startUp():
    '''This function allows easy resetting to the global defaults
    If the environment contains 'RL_xxx' then we use the value
    else we use the given default'''
    import os, sys
    global sys_version, _unset_
    sys_version = sys.version.split()[0]        #strip off the other garbage
    from reportlab.lib import pagesizes
    from reportlab.lib.utils import rl_isdir

    if _SAVED=={}:
        _unset_ = getattr(sys,'_rl_config__unset_',None)
        if _unset_ is None:
            class _unset_: pass
            sys._rl_config__unset_ = _unset_ = _unset_()
        global __all__
        A = list(__all__)
        for k,v in _DEFAULTS.items():
            _SAVED[k] = globals()[k] = v
            if k not in __all__:
                A.append(k)
        __all__ = tuple(A)

    #places to search for Type 1 Font files
    import reportlab
    D = {'REPORTLAB_DIR': os.path.abspath(os.path.dirname(reportlab.__file__)),
        'CWD': os.getcwd(),
        'disk': os.getcwd().split(':')[0],
        'sys_version': sys_version,
        'XDG_DATA_HOME': os.environ.get('XDG_DATA_HOME','~/.local/share'),
        }

    for k in _SAVED:
        if k.endswith('SearchPath'):
            P=[]
            for p in _SAVED[k]:
                d = (p % D).replace('/',os.sep)
                if '~' in d:
                    try:
                        d = os.path.expanduser(d)   #appengine fails with KeyError/ImportError (dev/live)
                    except (KeyError, ImportError):
                        continue
                if rl_isdir(d): P.append(d)
            _setOpt(k,os.pathsep.join(P),lambda x:x.split(os.pathsep))
            globals()[k] = list(filter(rl_isdir,globals()[k]))
        else:
            v = _SAVED[k]
            if isinstance(v,(int,float)):
                conv = type(v)
            elif k=='defaultPageSize':
                conv = lambda v,M=pagesizes: getattr(M,v)
            elif k in ('trustedHosts','trustedSchemes'):
                conv = lambda v: None if v is None else [y for y in [x.strip() for x in v.split(',')] if y] if isinstance(v,str) else v
            else: conv = None
            _setOpt(k,v,conv)

_registered_resets=[]
def register_reset(func):
    '''register a function to be called by rl_config._reset'''
    _registered_resets[:] = [x for x in _registered_resets if x()]
    L = [x for x in _registered_resets if x() is func]
    if L: return
    from weakref import ref
    _registered_resets.append(ref(func))

def _reset():
    '''attempt to reset reportlab and friends'''
    _startUp()  #our reset
    for f in _registered_resets[:]:
        c = f()
        if c:
            c()
        else:
            _registered_resets.remove(f)

_startUp()
