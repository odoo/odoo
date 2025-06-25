# Copyright 2018 gevent contributors. See LICENSE for details.

import os
import unittest
import sys

from gevent import _config

class TestResolver(unittest.TestCase):

    old_resolver = None

    def setUp(self):
        if 'GEVENT_RESOLVER' in os.environ:
            self.old_resolver = os.environ['GEVENT_RESOLVER']
            del os.environ['GEVENT_RESOLVER']

    def tearDown(self):
        if self.old_resolver:
            os.environ['GEVENT_RESOLVER'] = self.old_resolver

    def test_key(self):
        self.assertEqual(_config.Resolver.environment_key, 'GEVENT_RESOLVER')

    def test_default(self):
        from gevent.resolver.thread import Resolver

        conf = _config.Resolver()
        self.assertEqual(conf.get(), Resolver)

    def test_env(self):
        from gevent.resolver.blocking import Resolver

        os.environ['GEVENT_RESOLVER'] = 'foo,bar,block,dnspython'

        conf = _config.Resolver()
        self.assertEqual(conf.get(), Resolver)

        os.environ['GEVENT_RESOLVER'] = 'dnspython'

        # The existing value is unchanged
        self.assertEqual(conf.get(), Resolver)

        # A new object reflects it
        try:
            from gevent.resolver.dnspython import Resolver as DResolver
        except ImportError: # pragma: no cover
            # dnspython is optional; skip it.
            import warnings
            warnings.warn('dnspython not installed')
        else:
            conf = _config.Resolver()

            self.assertEqual(conf.get(), DResolver)

    def test_set_str_long(self):
        from gevent.resolver.blocking import Resolver
        conf = _config.Resolver()
        conf.set('gevent.resolver.blocking.Resolver')

        self.assertEqual(conf.get(), Resolver)

    def test_set_str_short(self):
        from gevent.resolver.blocking import Resolver
        conf = _config.Resolver()
        conf.set('block')

        self.assertEqual(conf.get(), Resolver)

    def test_set_class(self):
        from gevent.resolver.blocking import Resolver
        conf = _config.Resolver()
        conf.set(Resolver)

        self.assertEqual(conf.get(), Resolver)


    def test_set_through_config(self):
        from gevent.resolver.thread import Resolver as Default
        from gevent.resolver.blocking import Resolver

        conf = _config.Config()
        self.assertEqual(conf.resolver, Default)

        conf.resolver = 'block'
        self.assertEqual(conf.resolver, Resolver)

class TestFunctions(unittest.TestCase):

    def test_validate_bool(self):
        self.assertTrue(_config.validate_bool('on'))
        self.assertTrue(_config.validate_bool('1'))
        self.assertFalse(_config.validate_bool('off'))
        self.assertFalse(_config.validate_bool('0'))
        self.assertFalse(_config.validate_bool(''))

        with self.assertRaises(ValueError):
            _config.validate_bool(' hmm ')

    def test_validate_invalid(self):
        with self.assertRaises(ValueError):
            _config.validate_invalid(self)

class TestConfig(unittest.TestCase):

    def test__dir__(self):
        self.assertEqual(sorted(_config.config.settings),
                         sorted(dir(_config.config)))

    def test_getattr(self):
        # Bypass the property that might be set here
        self.assertIsNotNone(_config.config.__getattr__('resolver'))

    def test__getattr__invalid(self):
        with self.assertRaises(AttributeError):
            getattr(_config.config, 'no_such_setting')

    def test_set_invalid(self):
        with self.assertRaises(AttributeError):
            _config.config.set('no such setting', True)

class TestImportableSetting(unittest.TestCase):

    def test_empty_list(self):
        i = _config.ImportableSetting()
        with self.assertRaisesRegex(ImportError,
                                    "Cannot import from empty list"):
            i._import_one_of([])

    def test_path_not_supported(self):
        import warnings
        i = _config.ImportableSetting()
        path = list(sys.path)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with self.assertRaisesRegex(ImportError,
                                        "Cannot import 'foo/bar/gevent.no_such_module'"):
                i._import_one('foo/bar/gevent.no_such_module')

        # We restored the path
        self.assertEqual(path, sys.path)

        # We did not issue a warning
        self.assertEqual(len(w), 0)

    def test_non_string(self):
        i = _config.ImportableSetting()
        self.assertIs(i._import_one(self), self)

    def test_get_options(self):
        i = _config.ImportableSetting()
        self.assertEqual({}, i.get_options())

        i.shortname_map = {'foo': 'bad/path'}
        options = i.get_options()
        self.assertIn('foo', options)

if __name__ == '__main__':
    unittest.main()
