from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase


class TestWebProperties(TransactionCase):
    def test_get_properties_base_definition(self):
        """Check that we can not get the base definition if we can not read the model."""
        self.env["properties.base.definition"].get_properties_base_definition("res.partner", "properties")

        def _check_access(mode):
            if mode == "read":
                raise AccessError("")

        with patch.object(self.registry['res.partner'], 'check_access', side_effect=_check_access), \
             self.assertRaises(AccessError):
            self.env["properties.base.definition"].get_properties_base_definition("res.partner", "properties")
