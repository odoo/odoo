# -*- coding: utf-8 -*-

import mock
import unittest

from openerp import api
from openerp.modules.registry import RegistryManager
from openerp.tests import common
from openerp.addons.connector import connector
from openerp.addons.connector.exception import RetryableJobError
from openerp.addons.connector.connector import (
    ConnectorEnvironment,
    ConnectorUnit,
    pg_try_advisory_lock,
)
from openerp.addons.connector.session import ConnectorSession


def mock_connector_unit(env):
    session = ConnectorSession(env.cr, env.uid,
                               context=env.context)
    backend_record = mock.Mock(name='BackendRecord')
    backend = mock.Mock(name='Backend')
    backend_record.get_backend.return_value = backend
    connector_env = connector.ConnectorEnvironment(backend_record,
                                                   session,
                                                   'res.users')
    return ConnectorUnit(connector_env)


class ConnectorHelpers(unittest.TestCase):

    def test_openerp_module_name(self):
        name = connector._get_openerp_module_name('openerp.addons.sale')
        self.assertEqual(name, 'sale')
        name = connector._get_openerp_module_name('sale')
        self.assertEqual(name, 'sale')


class TestConnectorUnit(unittest.TestCase):
    """ Test Connector Unit """

    def test_connector_unit_for_model_names(self):
        model = 'res.users'

        class ModelUnit(ConnectorUnit):
            _model_name = model

        self.assertEqual(ModelUnit.for_model_names, [model])

    def test_connector_unit_for_model_names_several(self):
        models = ['res.users', 'res.partner']

        class ModelUnit(ConnectorUnit):
            _model_name = models

        self.assertEqual(ModelUnit.for_model_names, models)

    def test_connector_unit_no_model_name(self):
        with self.assertRaises(NotImplementedError):
            ConnectorUnit.for_model_names  # pylint: disable=W0104

    def test_match(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        session = mock.Mock(name='Session')

        self.assertTrue(ModelUnit.match(session, 'res.users'))
        self.assertFalse(ModelUnit.match(session, 'res.partner'))

    def test_unit_for(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        class ModelBinder(ConnectorUnit):
            _model_name = 'res.users'

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        # backend.get_class() is tested in test_backend.py
        backend.get_class.return_value = ModelUnit
        connector_env = connector.ConnectorEnvironment(backend_record,
                                                       session,
                                                       'res.users')
        unit = ConnectorUnit(connector_env)
        # returns an instance of ModelUnit with the same connector_env
        new_unit = unit.unit_for(ModelUnit)
        self.assertEqual(type(new_unit), ModelUnit)
        self.assertEqual(new_unit.connector_env, connector_env)

        backend.get_class.return_value = ModelBinder
        # returns an instance of ModelBinder with the same connector_env
        new_unit = unit.binder_for()
        self.assertEqual(type(new_unit), ModelBinder)
        self.assertEqual(new_unit.connector_env, connector_env)

    def test_unit_for_other_model(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.partner'

        class ModelBinder(ConnectorUnit):
            _model_name = 'res.partner'

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        # backend.get_class() is tested in test_backend.py
        backend.get_class.return_value = ModelUnit
        connector_env = connector.ConnectorEnvironment(backend_record,
                                                       session,
                                                       'res.users')
        unit = ConnectorUnit(connector_env)
        # returns an instance of ModelUnit with a new connector_env
        # for the different model
        new_unit = unit.unit_for(ModelUnit, model='res.partner')
        self.assertEqual(type(new_unit), ModelUnit)
        self.assertNotEqual(new_unit.connector_env, connector_env)
        self.assertEqual(new_unit.connector_env.model_name, 'res.partner')

        backend.get_class.return_value = ModelBinder
        # returns an instance of ModelBinder with a new connector_env
        # for the different model
        new_unit = unit.binder_for(model='res.partner')
        self.assertEqual(type(new_unit), ModelBinder)
        self.assertNotEqual(new_unit.connector_env, connector_env)
        self.assertEqual(new_unit.connector_env.model_name, 'res.partner')


class TestConnectorUnitTransaction(common.TransactionCase):

    def test_instance(self):

        class ModelUnit(ConnectorUnit):
            _model_name = 'res.users'

        unit = mock_connector_unit(self.env)
        self.assertEqual(unit.model, self.env['res.users'])
        self.assertEqual(unit.env, self.env)
        self.assertEqual(unit.localcontext, self.env.context)


class TestConnectorEnvironment(unittest.TestCase):

    def test_create_environment_no_connector_env(self):
        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        model = 'res.user'

        connector_env = ConnectorEnvironment.create_environment(
            backend_record, session, model
        )

        self.assertEqual(type(connector_env), ConnectorEnvironment)

    def test_create_environment_existing_connector_env(self):

        class MyConnectorEnvironment(ConnectorEnvironment):
            _propagate_kwargs = ['api']

            def __init__(self, backend_record, session, model_name, api=None):
                super(MyConnectorEnvironment, self).__init__(backend_record,
                                                             session,
                                                             model_name)
                self.api = api

        session = mock.MagicMock(name='Session')
        backend_record = mock.Mock(name='BackendRecord')
        backend = mock.Mock(name='Backend')
        backend_record.get_backend.return_value = backend
        model = 'res.user'
        api = object()

        cust_env = MyConnectorEnvironment(backend_record, session, model,
                                          api=api)

        new_env = cust_env.create_environment(backend_record, session, model,
                                              connector_env=cust_env)

        self.assertEqual(type(new_env), MyConnectorEnvironment)
        self.assertEqual(new_env.api, api)


class TestAdvisoryLock(common.TransactionCase):

    def setUp(self):
        super(TestAdvisoryLock, self).setUp()
        self.registry2 = RegistryManager.get(common.get_db_name())
        self.cr2 = self.registry2.cursor()
        self.env2 = api.Environment(self.cr2, self.env.uid, {})

        @self.addCleanup
        def reset_cr2():
            # rollback and close the cursor, and reset the environments
            self.env2.reset()
            self.cr2.rollback()
            self.cr2.close()

    def test_concurrent_lock(self):
        """ 2 concurrent transactions cannot acquire the same lock """
        lock = 'import_record({}, {}, {}, {})'.format(
            'backend.name',
            1,
            'res.partner',
            '999999',
        )
        acquired = pg_try_advisory_lock(self.env, lock)
        self.assertTrue(acquired)
        inner_acquired = pg_try_advisory_lock(self.env2, lock)
        self.assertFalse(inner_acquired)

    def test_concurrent_import_lock(self):
        """ A 2nd concurrent transaction must retry """
        lock = 'import_record({}, {}, {}, {})'.format(
            'backend.name',
            1,
            'res.partner',
            '999999',
        )
        connector_unit = mock_connector_unit(self.env)
        connector_unit.advisory_lock_or_retry(lock)
        connector_unit2 = mock_connector_unit(self.env2)
        with self.assertRaises(RetryableJobError) as cm:
            connector_unit2.advisory_lock_or_retry(lock, retry_seconds=3)
            self.assertEquals(cm.exception.seconds, 3)
