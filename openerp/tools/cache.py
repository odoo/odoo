import lru

class ormcache(object):
    """ LRU cache decorator for orm methods,
    """

    def __init__(self, skiparg=2, size=8192, multi=None, timeout=None):
        self.skiparg = skiparg
        self.size = size
        self.method = None
        self.stat_miss = 0
        self.stat_hit = 0
        self.stat_err = 0

    def __call__(self,m):
        self.method = m
        def lookup(self2, cr, *args):
            r = self.lookup(self2, cr, *args)
            return r
        lookup.clear_cache = self.clear
        return lookup

    def stat(self):
        return "lookup-stats hit=%s miss=%s err=%s ratio=%.1f" % (self.stat_hit,self.stat_miss,self.stat_err, (100*float(self.stat_hit))/(self.stat_miss+self.stat_hit) )

    def lru(self, self2):
        try:
            ormcache = getattr(self2, '_ormcache')
        except AttributeError:
            ormcache = self2._ormcache = {}
        try:
            d = ormcache[self.method]
        except KeyError:
            d = ormcache[self.method] = lru.LRU(self.size)
        return d

    def lookup(self, self2, cr, *args):
        d = self.lru(self2)
        key = args[self.skiparg-2:]
        try:
           r = d[key]
           self.stat_hit += 1
           return r
        except KeyError:
           self.stat_miss += 1
           value = d[key] = self.method(self2, cr, *args)
           return value
        except TypeError:
           self.stat_err += 1
           return self.method(self2, cr, *args)

    def clear(self, self2, *args):
        """ Remove *args entry from the cache or all keys if *args is undefined 
        """
        d = self.lru(self2)
        if args:
            try:
                key = args[self.skiparg-2:]
                del d[key]
                self2.pool._any_cache_cleared = True
            except KeyError:
                pass
        else:
            d.clear()
            self2.pool._any_cache_cleared = True

class ormcache_multi(ormcache):
    def __init__(self, skiparg=2, size=8192, multi=3):
        super(ormcache_multi,self).__init__(skiparg,size)
        self.multi = multi - 2

    def lookup(self, self2, cr, *args):
        d = self.lru(self2)
        args = list(args)
        multi = self.multi
        ids = args[multi]
        r = {}
        miss = []

        for i in ids:
            args[multi] = i
            key = tuple(args[self.skiparg-2:])
            try:
               r[i] = d[key]
               self.stat_hit += 1
            except Exception:
               self.stat_miss += 1
               miss.append(i)

        if miss:
            args[multi] = miss
            r.update(self.method(self2, cr, *args))

        for i in miss:
            args[multi] = i
            key = tuple(args[self.skiparg-2:])
            d[key] = r[i]

        return r

class dummy_cache(object):
    """ Cache decorator replacement to actually do no caching.
    """
    def __init__(self, *l, **kw):
        pass
    def __call__(self, fn):
        fn.clear_cache = self.clear
        return fn
    def clear(self, *l, **kw):
        pass

if __name__ == '__main__':

    class A():
        @ormcache()
        def m(self,a,b):
            print  "A::m(", self,a,b
            return 1

        @ormcache_multi(multi=3)
        def n(self,cr,uid,ids):
            print  "m", self,cr,uid,ids
            return dict([(i,i) for i in ids])

    a=A()
    r=a.m(1,2)
    r=a.m(1,2)
    r=a.n("cr",1,[1,2,3,4])
    r=a.n("cr",1,[1,2])
    print r
    for i in a._ormcache:
        print a._ormcache[i].d
    a.n.clear_cache(a,1,1)
    r=a.n("cr",1,[1,2])
    print r
    r=a.n("cr",1,[1,2])

# For backward compatibility
cache = ormcache

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
