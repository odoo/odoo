from mako import exceptions

try:
    from beaker import cache
    cache = cache.CacheManager()
except ImportError:
    cache = None

class Cache(object):
    def __init__(self, id, starttime):
        self.id = id
        self.starttime = starttime
        self.def_regions = {}
        
    def put(self, key, value, **kwargs):
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
        
        self._get_cache(defname, **kwargs).put_value(key, starttime=self.starttime, expiretime=expiretime)
        
    def get(self, key, **kwargs):
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
        
        return self._get_cache(defname, **kwargs).get_value(key, starttime=self.starttime, expiretime=expiretime, createfunc=createfunc)
        
    def invalidate(self, key, **kwargs):
        defname = kwargs.pop('defname', None)
        expiretime = kwargs.pop('expiretime', None)
        createfunc = kwargs.pop('createfunc', None)
        
        self._get_cache(defname, **kwargs).remove_value(key, starttime=self.starttime, expiretime=expiretime)
    
    def invalidate_body(self):
        self.invalidate('render_body', defname='render_body')
    
    def invalidate_def(self, name):
        self.invalidate('render_%s' % name, defname='render_%s' % name)
        
    def invalidate_closure(self, name):
        self.invalidate(name, defname=name)
    
    def _get_cache(self, defname, type=None, **kw):
        if not cache:
            raise exceptions.RuntimeException("the Beaker package is required to use cache functionality.")
        if type == 'memcached':
            type = 'ext:memcached'
        if not type:
            (type, kw) = self.def_regions.get(defname, ('memory', {}))
        else:
            self.def_regions[defname] = (type, kw)
        return cache.get_cache(self.id, type=type, **kw)
        