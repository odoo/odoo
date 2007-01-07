#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/lib/attrmap.py
__version__=''' $Id: attrmap.py 2741 2005-12-07 21:52:33Z andy $ '''
from UserDict import UserDict
from reportlab.lib.validators import isAnything, _SequenceTypes, DerivedValue
from reportlab import rl_config

class CallableValue:
    '''a class to allow callable initial values'''
    def __init__(self,func,*args,**kw):
        #assert iscallable(func)
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self):
        return apply(self.func,self.args,self.kw)

class AttrMapValue:
    '''Simple multi-value holder for attribute maps'''
    def __init__(self,validate=None,desc=None,initial=None, **kw):
        self.validate = validate or isAnything
        self.desc = desc
        self._initial = initial
        for k,v in kw.items():
            setattr(self,k,v)

    def __getattr__(self,name):
        #hack to allow callable initial values
        if name=='initial':
            if isinstance(self._initial,CallableValue): return self._initial()
            return self._initial
        elif name=='hidden':
            return 0
        raise AttributeError, name

class AttrMap(UserDict):
    def __init__(self,BASE=None,UNWANTED=[],**kw):
        data = {}
        if BASE:
            if isinstance(BASE,AttrMap):
                data = BASE.data                        #they used BASECLASS._attrMap
            else:
                if type(BASE) not in (type(()),type([])): BASE = (BASE,)
                for B in BASE:
                    if hasattr(B,'_attrMap'):
                        data.update(getattr(B._attrMap,'data',{}))
                    else:
                        raise ValueError, 'BASE=%s has wrong kind of value' % str(B)

        UserDict.__init__(self,data)
        self.remove(UNWANTED)
        self.data.update(kw)

    def update(self,kw):
        if isinstance(kw,AttrMap): kw = kw.data
        self.data.update(kw)

    def remove(self,unwanted):
        for k in unwanted:
            try:
                del self[k]
            except KeyError:
                pass

    def clone(self,UNWANTED=[],**kw):
        c = AttrMap(BASE=self,UNWANTED=UNWANTED)
        c.update(kw)
        return c

def validateSetattr(obj,name,value):
    '''validate setattr(obj,name,value)'''
    if rl_config.shapeChecking:
        map = obj._attrMap
        if map and name[0]!= '_':
            #we always allow the inherited values; they cannot
            #be checked until draw time.
            if isinstance(value, DerivedValue):
                #let it through
                pass
            else:            
                try:
                    validate = map[name].validate
                    if not validate(value):
                        raise AttributeError, "Illegal assignment of '%s' to '%s' in class %s" % (value, name, obj.__class__.__name__)
                except KeyError:
                    raise AttributeError, "Illegal attribute '%s' in class %s" % (name, obj.__class__.__name__)
    obj.__dict__[name] = value

def _privateAttrMap(obj,ret=0):
    '''clone obj._attrMap if required'''
    A = obj._attrMap
    oA = getattr(obj.__class__,'_attrMap',None)
    if ret:
        if oA is A:
            return A.clone(), oA
        else:
            return A, None
    else:
        if oA is A:
            obj._attrMap = A.clone()

def _findObjectAndAttr(src, P):
    '''Locate the object src.P for P a string, return parent and name of attribute
    '''
    P = string.split(P, '.')
    if len(P) == 0:
        return None, None
    else:
        for p in P[0:-1]:
            src = getattr(src, p)
        return src, P[-1]

def hook__setattr__(obj):
    if not hasattr(obj,'__attrproxy__'):
        C = obj.__class__
        import new
        obj.__class__=new.classobj(C.__name__,(C,)+C.__bases__,
            {'__attrproxy__':[],
            '__setattr__':lambda self,k,v,osa=getattr(obj,'__setattr__',None),hook=hook: hook(self,k,v,osa)})

def addProxyAttribute(src,name,validate=None,desc=None,initial=None,dst=None):
    '''
    Add a proxy attribute 'name' to src with targets dst
    '''
    #sanity
    assert hasattr(src,'_attrMap'), 'src object has no _attrMap'
    A, oA = _privateAttrMap(src,1)
    if type(dst) not in _SequenceTypes: dst = dst,
    D = []
    DV = []
    for d in dst:
        if type(d) in _SequenceTypes:
            d, e = d[0], d[1:]
        obj, attr = _findObjectAndAttr(src,d)
        if obj:
            dA = getattr(obj,'_attrMap',None)
