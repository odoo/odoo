# Copyright 2019 Eugene Molotov <https://github.com/em230418>
# License MIT (https://opensource.org/licenses/MIT).

import odoo.tests

from ..models.ir_translation import debrand_bytes


@odoo.tests.common.tagged("at_install", "post_install")
class TestMisc(odoo.tests.TransactionCase):
    def test_debrand_bytes(self):
        env = self.env
        env["ir.config_parameter"].sudo().set_param(
            "web_debranding.new_name", "SuperName"
        )
        assert debrand_bytes(env, b"odoo") == b"SuperName"
        assert debrand_bytes(env, "odoo") == b"SuperName"
        assert debrand_bytes(env, b"test") == b"test"
        assert debrand_bytes(env, "test") == b"test"
