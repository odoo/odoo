from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged, users


@tagged('at_install', '-post_install')
class TestWebProperties(TransactionCase):
    @users('admin')
    def test_get_properties_base_definition(self):
        """Check that we can not get the base definition if we can not read the model."""
        self.env["properties.base.definition"].get_properties_base_definition("res.partner", "properties")

        def raise_access(*a, **kw):
            raise AccessError('no access')

        with patch.object(self.registry['res.partner'], 'check_access', raise_access), \
             self.assertRaises(AccessError):
            self.env["properties.base.definition"].get_properties_base_definition("res.partner", "properties")
