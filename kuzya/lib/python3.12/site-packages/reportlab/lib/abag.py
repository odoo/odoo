#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/abag.py
__version__='3.3.0'
__doc__='''Data structure to hold a collection of attributes, used by styles.'''
class ABag:
    """
    'Attribute Bag' - a trivial BAG class for holding attributes.

    This predates modern Python.  Doing this again, we'd use a subclass
    of dict.

    You may initialize with keyword arguments.
    a = ABag(k0=v0,....,kx=vx,....) ==> getattr(a,'kx')==vx

    c = a.clone(ak0=av0,.....) copy with optional additional attributes.
    """
    def __init__(self,**attr):
        self.__dict__.update(attr)

    def clone(self,**attr):
        n = self.__class__(**self.__dict__)
        if attr: n.__dict__.update(attr)
        return n

    def __repr__(self):
        D = self.__dict__
        K = list(D.keys())
        K.sort()
        return '%s(%s)' % (self.__class__.__name__,', '.join(['%s=%r' % (k,D[k]) for k in K]))

if __name__=="__main__":
    AB = ABag(a=1, c="hello")
    CD = AB.clone()
    print(AB)
    print(CD)
