# -*- coding: utf-8 -*-

import unittest

import openerp.tests.common as common
from openerp.addons.connector.backend import (Backend,
                                              get_backend,
                                              BACKENDS)
from openerp.addons.connector.exception import NoConnectorUnitError
from openerp.addons.connector.connector import (Binder,
                                                ConnectorUnit)
from openerp.addons.connector.unit.mapper import ExportMapper
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.session import ConnectorSession


class test_backend(unittest.TestCase):
    """ Test Backend """

    def setUp(self):
        super(test_backend, self).setUp()
        self.service = 'calamitorium'

    def tearDown(self):
        super(test_backend, self).tearDown()
        BACKENDS.backends.clear()

    def test_new_backend(self):
        """ Create a backend"""
        version = '1.14'
        backend = Backend(self.service, version=version)
        self.assertEqual(backend.service, self.service)
        self.assertEqual(backend.version, version)

    def test_parent(self):
        """ Bind the backend to a parent backend"""
        version = '1.14'
        backend = Backend(self.service)
        child_backend = Backend(parent=backend, version=version)
        self.assertEqual(child_backend.service, backend.service)

    def test_no_service(self):
        """ Should raise an error because no service or parent is defined"""
        with self.assertRaises(ValueError):
            Backend(version='1.14')

    def test_get_backend(self):
        """ Find a backend """
        backend = Backend(self.service)
        found_ref = get_backend(self.service)
        self.assertEqual(backend, found_ref)

    def test_no_backend_found(self):
        """ Can't find a backend """
        with self.assertRaises(ValueError):
            get_backend('torium')

    def test_backend_version(self):
        """ Find a backend with a version """
        parent = Backend(self.service)
        backend = Backend(parent=parent, version='1.14')
        found_ref = get_backend(self.service, version='1.14')
        self.assertEqual(backend, found_ref)

    def test_repr(self):
        parent = Backend(self.service)
        self.assertEqual(str(parent), "Backend('calamitorium')")
        self.assertEqual(repr(parent), "<Backend 'calamitorium'>")

        backend = Backend(parent=parent, version='1.14')
        self.assertEqual(str(backend), "Backend('calamitorium', '1.14')")
        self.assertEqual(repr(backend), "<Backend 'calamitorium', '1.14'>")


class test_backend_register(common.TransactionCase):
    """ Test registration of classes on the Backend"""

    def setUp(self):
        super(test_backend_register, self).setUp()
        self.service = 'calamitorium'
        self.version = '1.14'
        self.parent = Backend(self.service)
        self.backend = Backend(parent=self.parent, version=self.version)
        self.session = ConnectorSession(self.cr,
                                        self.uid)

    def tearDown(self):
        super(test_backend_register, self).tearDown()
        BACKENDS.backends.clear()
        del self.backend._class_entries[:]

    def test_register_class(self):
        class BenderBinder(Binder):
            _model_name = 'res.users'

        self.backend.register_class(BenderBinder)
        ref = self.backend.get_class(Binder,
                                     self.session,
                                     'res.users')
        self.assertEqual(ref, BenderBinder)

    def test_register_class_decorator(self):
        @self.backend
        class ZoidbergMapper(ExportMapper):
            _model_name = 'res.users'

        ref = self.backend.get_class(ExportMapper,
                                     self.session,
                                     'res.users')
        self.assertEqual(ref, ZoidbergMapper)

    def test_register_class_parent(self):
        """ It should get the parent's class when no class is defined"""
        @self.parent
        class FryBinder(Binder):
            _model_name = 'res.users'

        ref = self.backend.get_class(Binder,
                                     self.session,
                                     'res.users')
        self.assertEqual(ref, FryBinder)

    def test_no_register_error(self):
        """ Error when asking for a class and none is found"""
        with self.assertRaises(NoConnectorUnitError):
            self.backend.get_class(BackendAdapter,
                                   self.session,
                                   'res.users')

    def test_get_class_installed_module(self):
        """ Only class from an installed module should be returned """
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaYesUnit(LambdaUnit):
            _model_name = 'res.users'

        class LambdaNoUnit(LambdaUnit):
            _model_name = 'res.users'

        # trick the origin of the class, let it think
        # that it comes from the OpenERP module 'not installed module'
        LambdaNoUnit._openerp_module_ = 'not installed module'
        self.backend(LambdaNoUnit)

        matching_cls = self.backend.get_class(LambdaUnit,
                                              self.session,
                                              'res.users')
        self.assertEqual(matching_cls, LambdaYesUnit)

    def test_get_class_replacing_module(self):
        """ Returns the replacing ConnectorUnit"""
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaNoUnit(LambdaUnit):
            _model_name = 'res.users'

        @self.backend(replacing=LambdaNoUnit)
        class LambdaYesUnit(LambdaUnit):
            _model_name = 'res.users'

        matching_cls = self.backend.get_class(LambdaUnit,
                                              self.session,
                                              'res.users')
        self.assertEqual(matching_cls, LambdaYesUnit)

    def test_get_class_replacing_uninstalled_module(self):
        """ Does not return the replacing ConnectorUnit of an
        uninstalled module """
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaYesUnit(LambdaUnit):
            _model_name = 'res.users'

        class LambdaNoUnit(LambdaUnit):
            _model_name = 'res.users'

        # trick the origin of the class, let it think
        # that it comes from the OpenERP module 'not installed module'
        LambdaNoUnit._openerp_module_ = 'not installed module'
        self.backend(LambdaNoUnit, replacing=LambdaYesUnit)

        matching_cls = self.backend.get_class(LambdaUnit,
                                              self.session,
                                              'res.users')
        self.assertEqual(matching_cls, LambdaYesUnit)

    def test_get_class_replacing_diamond(self):
        """ Replace several classes in a diamond fashion """
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaNoUnit(LambdaUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaNo2Unit(LambdaUnit):
            _model_name = 'res.users'

        @self.backend(replacing=(LambdaNoUnit, LambdaNo2Unit))
        class LambdaYesUnit(LambdaUnit):
            _model_name = 'res.users'

        matching_cls = self.backend.get_class(LambdaUnit,
                                              self.session,
                                              'res.users')
        self.assertEqual(matching_cls, LambdaYesUnit)

    def test_get_class_replacing_unregistered(self):
        """ Replacing an unregistered class raise ValueError """
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        with self.assertRaises(ValueError):
            @self.backend(replacing=LambdaUnit)
            class LambdaNoUnit(LambdaUnit):
                _model_name = 'res.users'

    def test_get_class_replacing_self(self):
        """ A class should not be able to replace itself """
        class LambdaUnit(ConnectorUnit):
            _model_name = 'res.users'

        @self.backend
        class LambdaRecurseUnit(LambdaUnit):
            _model_name = 'res.users'

        with self.assertRaises(ValueError):
            self.backend.register_class(LambdaRecurseUnit,
                                        replacing=LambdaRecurseUnit)
