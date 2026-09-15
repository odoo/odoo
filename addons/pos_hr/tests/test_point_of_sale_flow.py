# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.exceptions import UserError


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_pos_hr_session_name_gap(self):
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        session.set_opening_control(0, None)
        current_session_name = session.name
        session.action_pos_session_closing_control()

        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        def _message_post_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.session'], "message_post", _message_post_patch):
            with self.assertRaises(UserError):
                session.set_opening_control(0, None)

        session.set_opening_control(0, None)
        self.assertEqual(int(session.name.split('/')[1]), int(current_session_name.split('/')[1]) + 1)

    def test_limited_partner_loading_includes_employee_work_contact(self):
        """
        An employee's work contact is used as the partner of the cash moves
        they register (see pos_hr CashMovePopup.partnerId), so it must always
        be loaded by the PoS frontend, even when the number of partners
        loaded is restricted by the 'point_of_sale.limited_customer_count'
        system parameter. Otherwise the work contact is not available
        frontend-side, the cash move ends up without a partner, and deleting
        it later crashes in delete_cash_in_out (partner_id.name is False).
        """
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_customer_count', 0)

        employee = self.env['hr.employee'].sudo().create({
            'name': 'Test Employee',
            'company_id': self.company.id,
        })
        self.assertTrue(employee.work_contact_id, "An employee should always have a work contact")

        self.pos_config_usd.write({'module_pos_hr': True})

        domain = self.env['res.partner']._load_pos_data_domain({'pos.order': []}, self.pos_config_usd)
        partners = self.env['res.partner'].search(domain)

        self.assertIn(
            employee.work_contact_id, partners,
            "The work contact of an employee allowed on the config must always be loaded, "
            "regardless of the limited partner loading count",
        )
