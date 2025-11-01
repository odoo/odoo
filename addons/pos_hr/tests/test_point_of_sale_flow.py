# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.exceptions import UserError


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleCommon):
    def test_pos_hr_session_name_gap(self):
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        session.set_opening_control(0, None)
        current_session_name = session.name
        session.action_pos_session_closing_control()

        self.pos_config.open_ui()
        session = self.pos_config.current_session_id

        def _message_post_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.session'], "message_post", _message_post_patch):
            with self.assertRaises(UserError):
                session.set_opening_control(0, None)

        session.set_opening_control(0, None)
        self.assertEqual(int(session.name.split('/')[1]), int(current_session_name.split('/')[1]) + 1)
