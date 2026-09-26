import gevent.testing as greentest
from copy import copy
# Comment the line below to see that the standard thread.local is working correct
from gevent import monkey; monkey.patch_all()


from threading import local
from threading import Thread

from zope import interface

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping # pylint:disable=deprecated-class

class ReadProperty(object):
    """A property that can be overridden"""

    # A non-data descriptor

    def __get__(self, inst, klass):
        return 42 if inst is not None else self


class A(local):
    __slots__ = ['initialized', 'obj']

    path = ''

    type_path = 'MyPath'

    read_property = ReadProperty()

    def __init__(self, obj):
        super(A, self).__init__()
        if not hasattr(self, 'initialized'):
            self.obj = obj
        self.path = ''


class Obj(object):
    pass

# These next two classes have to be global to avoid the leakchecks
deleted_sentinels = []
created_sentinels = []

class Sentinel(object):
    def __del__(self):
        deleted_sentinels.append(id(self))


class MyLocal(local):

    CLASS_PROP = 42

    def __init__(self):
        local.__init__(self)
        self.sentinel = Sentinel()
        created_sentinels.append(id(self.sentinel))

    @property
    def desc(self):
        return self

class MyLocalSubclass(MyLocal):
    pass

class WithGetattr(local):

    def __getattr__(self, name):
        if name == 'foo':
            return 42
        return super(WithGetattr, self).__getattr__(name) # pylint:disable=no-member

class LocalWithABC(local, Mapping):

    def __getitem__(self, name):
        return self.d[name]

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

class LocalWithStaticMethod(local):

    @staticmethod
    def a_staticmethod():
        return 42

class LocalWithClassMethod(local):

    @classmethod
    def a_classmethod(cls):
        return cls




class TestGeventLocal(greentest.TestCase):
    # pylint:disable=attribute-defined-outside-init,blacklisted-name

    def setUp(self):
        del deleted_sentinels[:]
        del created_sentinels[:]

    tearDown = setUp

    def test_create_local_subclass_init_args(self):
        with self.assertRaisesRegex(TypeError,
                                    "Initialization arguments are not supported"):
            local("foo")

        with self.assertRaisesRegex(TypeError,
                                    "Initialization arguments are not supported"):
            local(kw="foo")


    def test_local_opts_not_subclassed(self):
        l = local()
        l.attr = 1
        self.assertEqual(l.attr, 1)

    def test_cannot_set_delete_dict(self):
        l = local()
        with self.assertRaises(AttributeError):
            l.__dict__ = 1

        with self.assertRaises(AttributeError):
            del l.__dict__

    def test_delete_with_no_dict(self):
        l = local()
        with self.assertRaises(AttributeError):
            delattr(l, 'thing')

        def del_local():
            with self.assertRaises(AttributeError):
                delattr(l, 'thing')

        t = Thread(target=del_local)
        t.start()
        t.join()

    def test_slot_and_type_attributes(self):
        a = A(Obj())
        a.initialized = 1
        self.assertEqual(a.initialized, 1)

        # The slot is shared
        def demonstrate_slots_shared():
            self.assertEqual(a.initialized, 1)
            a.initialized = 2

        greenlet = Thread(target=demonstrate_slots_shared)
        greenlet.start()
        greenlet.join()

        self.assertEqual(a.initialized, 2)

        # The slot overrides dict values
        a.__dict__['initialized'] = 42 # pylint:disable=unsupported-assignment-operation
        self.assertEqual(a.initialized, 2)

        # Deleting the slot deletes the slot, but not the dict
        del a.initialized
        self.assertFalse(hasattr(a, 'initialized'))
        self.assertIn('initialized', a.__dict__)

        # We can delete the 'path' ivar
        # and fall back to the type
        del a.path
        self.assertEqual(a.path, '')

        with self.assertRaises(AttributeError):
            del a.path

        # A read property calls get
        self.assertEqual(a.read_property, 42)
        a.read_property = 1
        self.assertEqual(a.read_property, 1)
        self.assertIsInstance(A.read_property, ReadProperty)

        # Type attributes can be read
        self.assertEqual(a.type_path, 'MyPath')
        self.assertNotIn('type_path', a.__dict__)

        # and replaced in the dict
        a.type_path = 'Local'
        self.assertEqual(a.type_path, 'Local')
        self.assertIn('type_path', a.__dict__)

    def test_attribute_error(self):
        # pylint:disable=attribute-defined-outside-init
        a = A(Obj())
        with self.assertRaises(AttributeError):
            getattr(a, 'fizz_buzz')

        def set_fizz_buzz():
            a.fizz_buzz = 1

        greenlet = Thread(target=set_fizz_buzz)
        greenlet.start()
        greenlet.join()

        with self.assertRaises(AttributeError):
            getattr(a, 'fizz_buzz')

    def test_getattr_called(self):
        getter = WithGetattr()
        self.assertEqual(42, getter.foo)
        getter.foo = 'baz'
        self.assertEqual('baz', getter.foo)


    def test_copy(self):
        a = A(Obj())
        a.path = '123'
        a.obj.echo = 'test'
        b = copy(a)

        # Copy makes a shallow copy. Meaning that the attribute path
        # has to be independent in the original and the copied object because the
        # value is a string, but the attribute obj should be just reference to
        # the instance of the class Obj

        self.assertEqual(a.path, b.path, 'The values in the two objects must be equal')
        self.assertEqual(a.obj, b.obj, 'The values must be equal')

        b.path = '321'
        self.assertNotEqual(a.path, b.path, 'The values in the two objects must be different')

        a.obj.echo = "works"
        self.assertEqual(a.obj, b.obj, 'The values must be equal')

    def test_copy_no_subclass(self):

        a = local()
        setattr(a, 'thing', 42)
        b = copy(a)
        self.assertEqual(b.thing, 42)
        self.assertIsNot(a.__dict__, b.__dict__)

    def test_objects(self):
        # Test which failed in the eventlet?!

        a = A({})
        a.path = '123'
        b = A({'one': 2})
        b.path = '123'
        self.assertEqual(a.path, b.path, 'The values in the two objects must be equal')

        b.path = '321'

        self.assertNotEqual(a.path, b.path, 'The values in the two objects must be different')

    def test_class_attr(self, kind=MyLocal):
        mylocal = kind()
        self.assertEqual(42, mylocal.CLASS_PROP)

        mylocal.CLASS_PROP = 1
        self.assertEqual(1, mylocal.CLASS_PROP)
        self.assertEqual(mylocal.__dict__['CLASS_PROP'], 1) # pylint:disable=unsubscriptable-object

        del mylocal.CLASS_PROP
        self.assertEqual(42, mylocal.CLASS_PROP)

        self.assertIs(mylocal, mylocal.desc)

    def test_class_attr_subclass(self):
        self.test_class_attr(kind=MyLocalSubclass)

    def test_locals_collected_when_greenlet_dead_but_still_referenced(self):
        # https://github.com/gevent/gevent/issues/387
        import gevent

        my_local = MyLocal()
        my_local.sentinel = None
        greentest.gc_collect_if_needed()

        del created_sentinels[:]
        del deleted_sentinels[:]

        def demonstrate_my_local():
            # Get the important parts
            getattr(my_local, 'sentinel')

        # Create and reference greenlets
        greenlets = [Thread(target=demonstrate_my_local) for _ in range(5)]
        for t in greenlets:
            t.start()
        gevent.sleep()

        self.assertEqual(len(created_sentinels), len(greenlets))

        for g in greenlets:
            assert not g.is_alive()
        gevent.sleep() # let the callbacks run
        greentest.gc_collect_if_needed()

        # The sentinels should be gone too
        self.assertEqual(len(deleted_sentinels), len(greenlets))

    @greentest.skipOnLibuvOnPyPyOnWin("GC makes this non-deterministic, especially on Windows")
    def test_locals_collected_when_unreferenced_even_in_running_greenlet(self):
        # In fact only on Windows do we see GC being an issue;
        # pypy2 5.0 on macos and travis don't have a problem.
        # https://github.com/gevent/gevent/issues/981
        import gevent
        import gc
        gc.collect()

        count = 1000

        running_greenlet = None

        def demonstrate_my_local():
            for _ in range(1000):
                x = MyLocal()
                self.assertIsNotNone(x.sentinel)
                x = None

            gc.collect()
            gc.collect()

            self.assertEqual(count, len(created_sentinels))
            # They're all dead, even though this greenlet is
            # still running
            self.assertEqual(count, len(deleted_sentinels))

            # The links were removed as well.
            self.assertFalse(running_greenlet.has_links())


        running_greenlet = gevent.spawn(demonstrate_my_local)
        gevent.sleep()
        running_greenlet.join()

        self.assertEqual(count, len(deleted_sentinels))

    @greentest.ignores_leakcheck
    def test_local_dicts_for_greenlet(self):
        import gevent
        from gevent.local import all_local_dicts_for_greenlet

        class MyGreenlet(gevent.Greenlet):
            results = None
            id_x = None
            def _run(self): # pylint:disable=method-hidden
                x = local()
                x.foo = 42
                self.id_x = id(x)
                self.results = all_local_dicts_for_greenlet(self)

        g = MyGreenlet()
        g.start()
        g.join()
        self.assertTrue(g.successful, g)
        self.assertEqual(g.results,
                         [((local, g.id_x), {'foo': 42})])

    def test_local_with_abc(self):
        # an ABC (or generally any non-exact-type) in the MRO doesn't
        # break things. See https://github.com/gevent/gevent/issues/1201

        x = LocalWithABC()
        x.d = {'a': 1}
        self.assertEqual({'a': 1}, x.d)
        # The ABC part works
        self.assertIn('a', x.d)
        self.assertEqual(['a'], list(x.keys()))

    def test_local_with_staticmethod(self):
        x = LocalWithStaticMethod()
        self.assertEqual(42, x.a_staticmethod())

    def test_local_with_classmethod(self):
        x = LocalWithClassMethod()
        self.assertIs(LocalWithClassMethod, x.a_classmethod())


class TestLocalInterface(greentest.TestCase):
    __timeout__ = None

    @greentest.ignores_leakcheck
    def test_provides(self):
        # https://github.com/gevent/gevent/issues/1122

        # pylint:disable=inherit-non-class
        class IFoo(interface.Interface):
            pass

        @interface.implementer(IFoo)
        class Base(object):
            pass

        class Derived(Base, local):
            pass

        d = Derived()
        p = list(interface.providedBy(d))
        self.assertEqual([IFoo], p)



@greentest.skipOnPurePython("Needs C extension")
class TestCExt(greentest.TestCase): # pragma: no cover

    def test_c_extension(self):
        self.assertEqual(local.__module__,
                         'gevent._gevent_clocal')

@greentest.skipWithCExtensions("Needs pure-python")
class TestPure(greentest.TestCase):

    def test_extension(self):
        self.assertEqual(local.__module__,
                         'gevent.local')


if __name__ == '__main__':
    greentest.main()
