# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Greenlet-local objects.

This module is based on `_threading_local.py`__ from the standard
library of Python 3.4.

__ https://github.com/python/cpython/blob/3.4/Lib/_threading_local.py

Greenlet-local objects support the management of greenlet-local data.
If you have data that you want to be local to a greenlet, simply create
a greenlet-local object and use its attributes:

  >>> import gevent
  >>> from gevent.local import local
  >>> mydata = local()
  >>> mydata.number = 42
  >>> mydata.number
  42

You can also access the local-object's dictionary:

  >>> mydata.__dict__
  {'number': 42}
  >>> mydata.__dict__.setdefault('widgets', [])
  []
  >>> mydata.widgets
  []

What's important about greenlet-local objects is that their data are
local to a greenlet. If we access the data in a different greenlet:

  >>> log = []
  >>> def f():
  ...     items = list(mydata.__dict__.items())
  ...     items.sort()
  ...     log.append(items)
  ...     mydata.number = 11
  ...     log.append(mydata.number)
  >>> greenlet = gevent.spawn(f)
  >>> greenlet.join()
  >>> log
  [[], 11]

we get different data.  Furthermore, changes made in the other greenlet
don't affect data seen in this greenlet:

  >>> mydata.number
  42

Of course, values you get from a local object, including a __dict__
attribute, are for whatever greenlet was current at the time the
attribute was read.  For that reason, you generally don't want to save
these values across greenlets, as they apply only to the greenlet they
came from.

You can create custom local objects by subclassing the local class:

  >>> class MyLocal(local):
  ...     number = 2
  ...     initialized = False
  ...     def __init__(self, **kw):
  ...         if self.initialized:
  ...             raise SystemError('__init__ called too many times')
  ...         self.initialized = True
  ...         self.__dict__.update(kw)
  ...     def squared(self):
  ...         return self.number ** 2

This can be useful to support default values, methods and
initialization.  Note that if you define an __init__ method, it will be
called each time the local object is used in a separate greenlet.  This
is necessary to initialize each greenlet's dictionary.

Now if we create a local object:

  >>> mydata = MyLocal(color='red')

Now we have a default number:

  >>> mydata.number
  2

an initial color:

  >>> mydata.color
  'red'
  >>> del mydata.color

And a method that operates on the data:

  >>> mydata.squared()
  4

As before, we can access the data in a separate greenlet:

  >>> log = []
  >>> greenlet = gevent.spawn(f)
  >>> greenlet.join()
  >>> log
  [[('color', 'red'), ('initialized', True)], 11]

without affecting this greenlet's data:

  >>> mydata.number
  2
  >>> mydata.color
  Traceback (most recent call last):
  ...
  AttributeError: 'MyLocal' object has no attribute 'color'

Note that subclasses can define slots, but they are not greenlet
local. They are shared across greenlets::

  >>> class MyLocal(local):
  ...     __slots__ = 'number'

  >>> mydata = MyLocal()
  >>> mydata.number = 42
  >>> mydata.color = 'red'

So, the separate greenlet:

  >>> greenlet = gevent.spawn(f)
  >>> greenlet.join()

affects what we see:

  >>> mydata.number
  11

>>> del mydata

.. versionchanged:: 1.1a2
   Update the implementation to match Python 3.4 instead of Python 2.5.
   This results in locals being eligible for garbage collection as soon
   as their greenlet exits.

.. versionchanged:: 1.2.3
   Use a weak-reference to clear the greenlet link we establish in case
   the local object dies before the greenlet does.

.. versionchanged:: 1.3a1
   Implement the methods for attribute access directly, handling
   descriptors directly here. This allows removing the use of a lock
   and facilitates greatly improved performance.

.. versionchanged:: 1.3a1
   The ``__init__`` method of subclasses of ``local`` is no longer
   called with a lock held. CPython does not use such a lock in its
   native implementation. This could potentially show as a difference
   if code that uses multiple dependent attributes in ``__slots__``
   (which are shared across all greenlets) switches during ``__init__``.

"""
from __future__ import print_function

from copy import copy
from weakref import ref


locals()['getcurrent'] = __import__('greenlet').getcurrent
locals()['greenlet_init'] = lambda: None

__all__ = [
    "local",
]

# The key used in the Thread objects' attribute dicts.
# We keep it a string for speed but make it unlikely to clash with
# a "real" attribute.
key_prefix = '_gevent_local_localimpl_'

# The overall structure is as follows:
# For each local() object:
# greenlet.__dict__[key_prefix + str(id(local))]
#    => _localimpl.dicts[id(greenlet)] => (ref(greenlet), {})

# That final tuple is actually a localimpl_dict_entry object.

def all_local_dicts_for_greenlet(greenlet):
    """
    Internal debug helper for getting the local values associated
    with a greenlet. This is subject to change or removal at any time.

    :return: A list of ((type, id), {}) pairs, where the first element
      is the type and id of the local object and the second object is its
      instance dictionary, as seen from this greenlet.

    .. versionadded:: 1.3a2
    """

    result = []
    id_greenlet = id(greenlet)
    greenlet_dict = greenlet.__dict__
    for k, v in greenlet_dict.items():
        if not k.startswith(key_prefix):
            continue
        local_impl = v()
        if local_impl is None:
            continue
        entry = local_impl.dicts.get(id_greenlet)
        if entry is None:
            # Not yet used in this greenlet.
            continue
        assert entry.wrgreenlet() is greenlet
        result.append((local_impl.localtypeid, entry.localdict))

    return result


class _wrefdict(dict):
    """A dict that can be weak referenced"""

class _greenlet_deleted(object):
    """
    A weakref callback for when the greenlet
    is deleted.

    If the greenlet is a `gevent.greenlet.Greenlet` and
    supplies ``rawlink``, that will be used instead of a
    weakref.
    """
    __slots__ = ('idt', 'wrdicts')

    def __init__(self, idt, wrdicts):
        self.idt = idt
        self.wrdicts = wrdicts

    def __call__(self, _unused):
        dicts = self.wrdicts()
        if dicts:
            dicts.pop(self.idt, None)

class _local_deleted(object):
    __slots__ = ('key', 'wrthread', 'greenlet_deleted')

    def __init__(self, key, wrthread, greenlet_deleted):
        self.key = key
        self.wrthread = wrthread
        self.greenlet_deleted = greenlet_deleted

    def __call__(self, _unused):
        thread = self.wrthread()
        if thread is not None:
            try:
                unlink = thread.unlink
            except AttributeError:
                pass
            else:
                unlink(self.greenlet_deleted)
            del thread.__dict__[self.key]

class _localimpl(object):
    """A class managing thread-local dicts"""
    __slots__ = ('key', 'dicts',
                 'localargs', 'localkwargs',
                 'localtypeid',
                 '__weakref__',)

    def __init__(self, args, kwargs, local_type, id_local):
        self.key = key_prefix + str(id(self))
        # { id(greenlet) -> _localimpl_dict_entry(ref(greenlet), greenlet-local dict) }
        self.dicts = _wrefdict()
        self.localargs = args
        self.localkwargs = kwargs
        self.localtypeid = local_type, id_local

        # We need to create the thread dict in anticipation of
        # __init__ being called, to make sure we don't call it
        # again ourselves. MUST do this before setting any attributes.
        greenlet = getcurrent() # pylint:disable=undefined-variable
        _localimpl_create_dict(self, greenlet, id(greenlet))

class _localimpl_dict_entry(object):
    """
    The object that goes in the ``dicts`` of ``_localimpl``
    object for each thread.
    """
    # This is a class, not just a tuple, so that cython can optimize
    # attribute access
    __slots__ = ('wrgreenlet', 'localdict')

    def __init__(self, wrgreenlet, localdict):
        self.wrgreenlet = wrgreenlet
        self.localdict = localdict

# We use functions instead of methods so that they can be cdef'd in
# local.pxd; if they were cdef'd as methods, they would cause
# the creation of a pointer and a vtable. This happens
# even if we declare the class @cython.final. functions thus save memory overhead
# (but not pointer chasing overhead; the vtable isn't used when we declare
# the class final).


def _localimpl_create_dict(self, greenlet, id_greenlet):
    """Create a new dict for the current thread, and return it."""
    localdict = {}
    key = self.key

    wrdicts = ref(self.dicts)

    # When the greenlet is deleted, remove the local dict.
    # Note that this is suboptimal if the greenlet object gets
    # caught in a reference loop. We would like to be called
    # as soon as the OS-level greenlet ends instead.

    # If we are working with a gevent.greenlet.Greenlet, we
    # can pro-actively clear out with a link, avoiding the
    # issue described above. Use rawlink to avoid spawning any
    # more greenlets.
    greenlet_deleted = _greenlet_deleted(id_greenlet, wrdicts)

    rawlink = getattr(greenlet, 'rawlink', None)
    if rawlink is not None:
        rawlink(greenlet_deleted)
        wrthread = ref(greenlet)
    else:
        wrthread = ref(greenlet, greenlet_deleted)


    # When the localimpl is deleted, remove the thread attribute.
    local_deleted = _local_deleted(key, wrthread, greenlet_deleted)


    wrlocal = ref(self, local_deleted)
    greenlet.__dict__[key] = wrlocal

    self.dicts[id_greenlet] = _localimpl_dict_entry(wrthread, localdict)
    return localdict


_marker = object()

def _local_get_dict(self):
    impl = self._local__impl
    # Cython can optimize dict[], but not dict.get()
    greenlet = getcurrent() # pylint:disable=undefined-variable
    idg = id(greenlet)
    try:
        entry = impl.dicts[idg]
        dct = entry.localdict
    except KeyError:
        dct = _localimpl_create_dict(impl, greenlet, idg)
        self.__init__(*impl.localargs, **impl.localkwargs)
    return dct

def _init():
    greenlet_init() # pylint:disable=undefined-variable

_local_attrs = {
    '_local__impl',
    '_local_type_get_descriptors',
    '_local_type_set_or_del_descriptors',
    '_local_type_del_descriptors',
    '_local_type_set_descriptors',
    '_local_type',
    '_local_type_vars',
    '__class__',
    '__cinit__',
}

class local(object):
    """
    An object whose attributes are greenlet-local.
    """
    __slots__ = tuple(_local_attrs - {'__class__', '__cinit__'})

    def __cinit__(self, *args, **kw): # pylint:disable=bad-dunder-name
        if args or kw:
            if type(self).__init__ == object.__init__: # pylint:disable=comparison-with-callable
                raise TypeError("Initialization arguments are not supported", args, kw)
        impl = _localimpl(args, kw, type(self), id(self))
        # pylint:disable=attribute-defined-outside-init
        self._local__impl = impl
        get, dels, sets_or_dels, sets = _local_find_descriptors(self)
        self._local_type_get_descriptors = get
        self._local_type_set_or_del_descriptors = sets_or_dels
        self._local_type_del_descriptors = dels
        self._local_type_set_descriptors = sets
        self._local_type = type(self)
        self._local_type_vars = set(dir(self._local_type))

    def __getattribute__(self, name): # pylint:disable=too-many-return-statements
        if name in _local_attrs:
            # The _local__impl,  __cinit__, etc, won't be hit by the
            # Cython version, if we've done things right. If we haven't,
            # they will be, and this will produce an error.
            return object.__getattribute__(self, name)

        dct = _local_get_dict(self)

        if name == '__dict__':
            return dct
        # If there's no possible way we can switch, because this
        # attribute is *not* found in the class where it might be a
        # data descriptor (property), and it *is* in the dict
        # then we don't need to swizzle the dict and take the lock.

        # We don't have to worry about people overriding __getattribute__
        # because if they did, the dict-swizzling would only last as
        # long as we were in here anyway.
        # Similarly, a __getattr__ will still be called by _oga() if needed
        # if it's not in the dict.

        # Optimization: If we're not subclassed, then
        # there can be no descriptors except for methods, which will
        # never need to use __dict__.
        if self._local_type is local:
            return dct[name] if name in dct else object.__getattribute__(self, name)

        # NOTE: If this is a descriptor, this will invoke its __get__.
        # A broken descriptor that doesn't return itself when called with
        # a None for the instance argument could mess us up here.
        # But this is faster than a loop over mro() checking each class __dict__
        # manually.
        if name in dct:
            if name not in self._local_type_vars:
                # If there is a dict value, and nothing in the type,
                # it can't possibly be a descriptor, so it is just returned.
                return dct[name]

            # It's in the type *and* in the dict. If the type value is
            # a data descriptor (defines __get__ *and* either __set__ or
            # __delete__), then the type wins. If it's a non-data descriptor
            # (defines just __get__), then the instance wins. If it's not a
            # descriptor at all (doesn't have __get__), the instance wins.
            # NOTE that the docs for descriptors say that these methods must be
            # defined on the *class* of the object in the type.
            if name not in self._local_type_get_descriptors:
                # Entirely not a descriptor. Instance wins.
                return dct[name]
            if name in self._local_type_set_or_del_descriptors:
                # A data descriptor.
                # arbitrary code execution while these run. If they touch self again,
                # they'll call back into us and we'll repeat the dance.
                type_attr = getattr(self._local_type, name)
                return type(type_attr).__get__(type_attr, self, self._local_type)
            # Last case is a non-data descriptor. Instance wins.
            return dct[name]

        if name in self._local_type_vars:
            # Not in the dictionary, but is found in the type. It could be
            # a non-data descriptor still. Some descriptors, like @staticmethod,
            # return objects (functions, in this case), that are *themselves*
            # descriptors, which when invoked, again, would do the wrong thing.
            # So we can't rely on getattr() on the type for them, we have to
            # look through the MRO dicts ourself.
            if name not in self._local_type_get_descriptors:
                # Not a descriptor, can't execute code. So all we need is
                # the return value of getattr() on our type.
                return getattr(self._local_type, name)

            for base in self._local_type.mro():
                bd = base.__dict__
                if name in bd:
                    attr_on_type = bd[name]
                    result = type(attr_on_type).__get__(attr_on_type, self, self._local_type)
                    return result

        # It wasn't in the dict and it wasn't in the type.
        # So the next step is to invoke type(self)__getattr__, if it
        # exists, otherwise raise an AttributeError.
        # we will invoke type(self).__getattr__ or raise an attribute error.
        if hasattr(self._local_type, '__getattr__'):
            return self._local_type.__getattr__(self, name)
        raise AttributeError("%r object has no attribute '%s'"
                             % (self._local_type.__name__, name))

    def __setattr__(self, name, value):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only"
                % type(self))

        if name in _local_attrs:
            object.__setattr__(self, name, value)
            return

        dct = _local_get_dict(self)

        if self._local_type is local:
            # Optimization: If we're not subclassed, we can't
            # have data descriptors, so this goes right in the dict.
            dct[name] = value
            return

        if name in self._local_type_vars:
            if name in self._local_type_set_descriptors:
                type_attr = getattr(self._local_type, name, _marker)
                # A data descriptor, like a property or a slot.
                type(type_attr).__set__(type_attr, self, value)
                return
        # Otherwise it goes directly in the dict
        dct[name] = value

    def __delattr__(self, name):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only"
                % self.__class__.__name__)

        if name in self._local_type_vars:
            if name in self._local_type_del_descriptors:
                # A data descriptor, like a property or a slot.
                type_attr = getattr(self._local_type, name, _marker)
                type(type_attr).__delete__(type_attr, self)
                return
        # Otherwise it goes directly in the dict

        # Begin inlined function _get_dict()
        dct = _local_get_dict(self)

        try:
            del dct[name]
        except KeyError:
            raise AttributeError(name)

    def __copy__(self):
        impl = self._local__impl
        entry = impl.dicts[id(getcurrent())]  # pylint:disable=undefined-variable

        dct = entry.localdict
        duplicate = copy(dct)

        cls = type(self)
        instance = cls(*impl.localargs, **impl.localkwargs)
        _local__copy_dict_from(instance, impl, duplicate)
        return instance

def _local__copy_dict_from(self, impl, duplicate):
    current = getcurrent() # pylint:disable=undefined-variable
    currentId = id(current)
    new_impl = self._local__impl
    assert new_impl is not impl
    entry = new_impl.dicts[currentId]
    new_impl.dicts[currentId] = _localimpl_dict_entry(entry.wrgreenlet, duplicate)

def _local_find_descriptors(self):
    type_self = type(self)
    gets = set()
    dels = set()
    set_or_del = set()
    sets = set()
    mro = list(type_self.mro())

    for attr_name in dir(type_self):
        # Conventionally, descriptors when called on a class
        # return themself, but not all do. Notable exceptions are
        # in the zope.interface package, where things like __provides__
        # return other class attributes. So we can't use getattr, and instead
        # walk up the dicts
        for base in mro:
            bd = base.__dict__
            if attr_name in bd:
                attr = bd[attr_name]
                break
        else:
            raise AttributeError(attr_name)

        type_attr = type(attr)
        if hasattr(type_attr, '__get__'):
            gets.add(attr_name)
        if hasattr(type_attr, '__delete__'):
            dels.add(attr_name)
            set_or_del.add(attr_name)
        if hasattr(type_attr, '__set__'):
            sets.add(attr_name)

    return (gets, dels, set_or_del, sets)

# Cython doesn't let us use __new__, it requires
# __cinit__. But we need __new__ if we're not compiled
# (e.g., on PyPy). So we set it at runtime. Cython
# will raise an error if we're compiled.
def __new__(cls, *args, **kw):
    self = super(local, cls).__new__(cls) # pylint:disable=no-value-for-parameter
    # We get the cls in *args for some reason
    # too when we do it this way....except on PyPy3, which does
    # not *unless* it's wrapped in a classmethod (which it is)
    self.__cinit__(*args[1:], **kw)
    return self

if local.__module__ == 'gevent.local':
    # PyPy2/3 and CPython handle adding a __new__ to the class
    # in different ways. In CPython and PyPy3, it must be wrapped with classmethod;
    # in PyPy2 < 7.3.3, it must not. In either case, the args that get passed to
    # it are stil wrong.
    #
    # Prior to Python 3.10, Cython-compiled classes were immutable and
    # raised a TypeError on assignment to __new__, and we relied on that
    # to detect the compiled version; but that breaks in
    # 3.10 as classes are now mutable. (See
    # https://github.com/cython/cython/issues/4326).
    #
    # That's OK; post https://github.com/gevent/gevent/issues/1480, the Cython-compiled
    # module has a different name than the pure-Python version and we can check for that.
    # It's not as direct, but it works.
    # So here we're not compiled
    local.__new__ = classmethod(__new__)
else: # pragma: no cover
    # Make sure we revisit in case of changes to the (accelerator) module names.
    if local.__module__ != 'gevent._gevent_clocal': # pylint:disable=else-if-used
        raise AssertionError("Module names changed (local: %r; __name__: %r); revisit this code" % (
            local.__module__, __name__) )

_init()

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent._local')
