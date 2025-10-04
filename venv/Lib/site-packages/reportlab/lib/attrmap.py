#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/attrmap.py
__version__='3.3.0'
__doc__='''Framework for objects whose assignments are checked. Used by graphics.

We developed reportlab/graphics prior to Python 2 and metaclasses. For the
graphics, we wanted to be able to declare the attributes of a class, check
them on assignment, and convert from string arguments.  Examples of
attrmap-based objects can be found in reportlab/graphics/shapes.  It lets
us defined structures like the one below, which are seen more modern form in
Django models and other frameworks.

We'll probably replace this one day soon, hopefully with no impact on client
code.

class Rect(SolidShape):
    """Rectangle, possibly with rounded corners."""

    _attrMap = AttrMap(BASE=SolidShape,
        x = AttrMapValue(isNumber),
        y = AttrMapValue(isNumber),
        width = AttrMapValue(isNumber),
        height = AttrMapValue(isNumber),
        rx = AttrMapValue(isNumber),
        ry = AttrMapValue(isNumber),
        )


'''
from reportlab.lib.validators import isAnything, DerivedValue
from reportlab.lib.utils import isSeq
from reportlab import rl_config

class CallableValue:
    '''a class to allow callable initial values'''
    def __init__(self,func,*args,**kw):
        #assert iscallable(func)
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self):
        return self.func(*self.args,**self.kw)

class AttrMapValue:
    '''Simple multi-value holder for attribute maps'''
    def __init__(self,validate=None,desc=None,initial=None, advancedUsage=0, **kw):
        self.validate = validate or isAnything
        self.desc = desc
        self._initial = initial
        self._advancedUsage = advancedUsage
        for k,v in kw.items():
            setattr(self,k,v)

    def __getattr__(self,name):
        #hack to allow callable initial values
        if name=='initial':
            if isinstance(self._initial,CallableValue): return self._initial()
            return self._initial
        elif name=='hidden':
            return 0
        raise AttributeError(name)

    def __repr__(self):
        return 'AttrMapValue(%s)' % ', '.join(['%s=%r' % i for i in self.__dict__.items()])

class AttrMap(dict):
    def __init__(self,BASE=None,UNWANTED=[],**kw):
        data = {}
        if BASE:
            if isinstance(BASE,AttrMap):
                data = BASE
            else:
                if not isSeq(BASE): BASE = (BASE,)
                for B in BASE:
                    am = getattr(B,'_attrMap',self)
                    if am is not self:
                        if am: data.update(am)
                    else:
                        raise ValueError('BASE=%s has wrong kind of value' % ascii(B))

        dict.__init__(self,data)
        self.remove(UNWANTED)
        self.update(kw)

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
                        raise AttributeError("Illegal assignment of '%s' to '%s' in class %s" % (value, name, obj.__class__.__name__))
                except KeyError:
                    raise AttributeError("Illegal attribute '%s' in class %s" % (name, obj.__class__.__name__))
    prop = getattr(obj.__class__,name,None)
    if isinstance(prop,property):
        try:
            prop.__set__(obj,value)
        except AttributeError:
            pass
    elif name=='__dict__':
        obj.__dict__.clear()
        obj.__dict__.update(value)
    else:
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
    P = P.split('.')
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
    if not isSeq(dst): dst = dst,
    D = []
    DV = []
    for d in dst:
        if isSeq(d):
            d, e = d[0], d[1:]
        obj, attr = _findObjectAndAttr(src,d)
        if obj:
            dA = getattr(obj,'_attrMap',None)
