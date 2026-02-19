# Copyright 2023 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from unittest import mock

from odoo.addons.component.utils import is_component_registry_ready

from .common import TransactionComponentRegistryCase


class TestUtils(TransactionComponentRegistryCase):
    def test_registry_ready(self):
        path = "odoo.addons.component.utils.get_component_registry"
        with mock.patch(path) as mocked:
            mocked.return_value = None
            self.assertFalse(is_component_registry_ready(self.env.cr.dbname))
            self._setup_registry(self)
            mocked.return_value = self.comp_registry
            self.assertTrue(is_component_registry_ready(self.env.cr.dbname))
            self._teardown_registry(self)
