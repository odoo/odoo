# -*- coding: utf-8 -*-
def _name(node):
    if node['type'] == 'Identifier':
        return node['name']
    if node['type'] == 'MemberExpression':
        return "%s.%s" % (_name(node['object']), _name(node['property']))
    raise ValueError("Unnamable node type %s" % node['type'])

def _value(node, strict=False):
    t = node['type']
    if t == 'Identifier':
        return node['name']
    elif t == 'Literal':
        return node['value']
    msg = '<%s has no value>' % _identify(node, {})
    if strict:
        raise ValueError(msg)
    return msg

def _identify(valnode, ns):
    if valnode is None:
        return "None"
    # already identified and re-set in the ns?
    if isinstance(valnode, Printable):
        return valnode

    # check other non-empty returns
    t = valnode['type']
    if t == "Literal":
        if valnode.get('regex'):
            return valnode['regex']['pattern']
        return valnode['value']
    elif t == "Identifier":
        n = valnode['name']
        return ns.get(n, Global(n))
    elif t == "NewExpression":
        return Instance(_identify(valnode['callee'], ns))
    elif t == "ObjectExpression":
        return Namespace({
            _value(prop['key']): _identify(prop['value'], ns)
            for prop in valnode['properties']
        })
    elif t == "MemberExpression":
        return Deref(
            _identify(valnode['object'], ns),
            _identify(valnode['property'], ns) if valnode['computed'] else valnode['property']['name'],
        )
    elif t == "CallExpression":
        return Call(
            _identify(valnode['callee'], ns),
            [_identify(arg, ns) for arg in valnode['arguments']],
        )
    elif t == 'BinaryExpression':
        return "%s %s %s" % (
            _identify(valnode['left'], ns),
            valnode['operator'],
            _identify(valnode['right'], ns),
        )
    else:
        return t

class Counter(object):
    __slots__ = ['_number']
    def __init__(self):
        self._number = 0

    def __bool__(self):
        return bool(self._number)
    __nonzero__ = __bool__
    def __int__(self):
        return self._number

    def get(self):
        return self._number
    def increment(self):
        self._number += 1
        return self._number
    def decrement(self):
        self._number -= 1
        return self._number

    def __enter__(self):
        self._number += 1
        return self._number
    def __exit__(self, *args):
        self._number -= 1

class Printable(object):
    __slots__ = []
    depth = Counter()
    def __repr__(self):
        with self.depth as i:
            if i > 2:
                return "%s(...)" % type(self).__name__
            return "%s(%s)" % (type(self).__name__, ', '.join(
                "%s=%r" % (k, getattr(self, k))
                for k in self.__slots__
                if not k.startswith('_')
                if getattr(self, k)
            ))


def resolve(obj, store):
    if obj is None:
        return None

    if isinstance(obj, (type(u''), bool, int, float)):
        return obj

    if isinstance(obj, ModuleProxy):
        return resolve(obj.get(), store)

    try:
        if getattr(obj, 'resolved', False):
            return obj
        return obj.resolve(store)
    except AttributeError:
        raise TypeError("Unresolvable {!r}".format(obj))

class Resolvable(Printable):
    """
    For types resolved in place
    """
    __slots__ = ['resolved']

    def __init__(self):
        super(Resolvable, self).__init__()
        self.resolved = False
    def resolve(self, store):
        self.resolved = True
        return self

class Namespace(Resolvable):
    __slots__ = ['attrs']
    def __init__(self, attrs):
        super(Namespace, self).__init__()
        self.attrs = attrs
    def resolve(self, store):
        r = super(Namespace, self).resolve(store)
        self.attrs = {
            k: resolve(v, store)
            for k, v in self.attrs.items()
        }
        return r
    def __getitem__(self, key):
        assert isinstance(key, type(u'')), "%r is not a namespace key" % key
        try:
            return self.attrs[key]
        except KeyError:
            return Global(self)[key]

class Module(Resolvable):
    __slots__ = ('name', 'comments', 'exports', 'augments', 'dependencies', '_store')
    def __init__(self, name, store, comments=()):
        super(Module, self).__init__()
        self.name = name
        self._store = store
        self.comments = tuple(comments)
        self.exports = None
        self.augments = []
        self.dependencies = set()
        store[name] = self
    def add_dependency(self, depname):
        dep = ModuleProxy(depname, self._store)
        self.dependencies.add(dep)
        return dep
    def get(self):
        return self
    def resolve(self, store=None):
        r = super(Module, self).resolve(store)
        self.exports = resolve(self.exports, self._store)
        self.augments = [resolve(a, self._store) for a in self.augments]
        self.dependencies = {
            resolve(d, self._store)
            for d in self.dependencies
        }
        return r
    def __getitem__(self, k):
        try:
            return self.exports[k]
        except KeyError:
            return Global(self)[k]

class ModuleProxy(object):
    def __init__(self, name, store):
        self.name = name
        self.store = store
    def get(self):
        # web.web_client is not an actual module
        return self.store.get(self.name, '<unstored %s>' % self.name)
    def __repr__(self):
        return repr(self.get())
    def __hash__(self):
        return hash(self.name)
    def __eq__(self, other):
        return self.name == other.name

class Class(Resolvable):
    __slots__ = ['name', 'members', 'extends', 'mixins', 'comments']
    def __init__(self, name, extends):
        super(Class, self).__init__()
        self.name = name
        self.extends = extends
        self.members = {}
        self.mixins = []
        self.comments = []

    def resolve(self, store):
        r = super(Class, self).resolve(store)
        self.extends = resolve(self.extends, store)
        self.mixins = [resolve(m, store) for m in self.mixins]
        return r

class Instance(Resolvable):
    __slots__ = ['type']
    def __init__(self, type):
        super(Instance, self).__init__()
        self.type = type

    def resolve(self, store):
        r = super(Instance, self).resolve(store)
        self.type = resolve(self.type, store)
        if isinstance(self.type, Module):
            self.type = self.type.exports
        return r

    def __getitem__(self, key):
        return Global(self)['key']

class Function(Resolvable):
    __slots__ = ['comments']
    def __init__(self, comments):
        super(Function, self).__init__()
        self.comments = comments

class Deref(Printable):
    __slots__ = ['object', 'property']
    def __init__(self, object, property):
        self.object = object
        self.property = property
    def resolve(self, store):
        return resolve(self.object, store)[self.property]

class Call(Resolvable):
    __slots__ = ['callable']
    def __init__(self, callable, arguments):
        super(Call, self).__init__()
        self.callable = callable
    def resolve(self, store):
        r = super(Call, self).resolve(store)
        self.callable = resolve(self.callable, store)
        return r
    def __getitem__(self, item):
        return Global(self)[item]

def get(node, it, *path):
    if not path:
        return node[it]
    return get(node[it], *path)


def match(node, pattern):
    """Checks that ``pattern`` is a subset of ``node``.

    If a sub-pattern is a callable it will be called with the current
    sub-node and its result is the match's. Other sub-patterns are
    checked by equality against the correspoding sub-node.

    Can be used to quickly check the descendants of a node of suitable
    type.

    TODO: support checking list content? Would be convenient to
          constraint e.g. CallExpression based on their parameters

    """
    if node is None and pattern is not None:
        return
    if callable(pattern):
        return pattern(node)
    if isinstance(node, list):
        return all(len(node) > i and match(node[i], v) for i, v in pattern.items())
    if isinstance(pattern, dict):
        return all(match(node.get(k), v) for k, v in pattern.items())
    return node == pattern


class Global(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return '<external %s>' % self.name
    def __getitem__(self, name):
        return Global('%s.%s' % (self.name, name))
    def resolve(self, store):
        return self
