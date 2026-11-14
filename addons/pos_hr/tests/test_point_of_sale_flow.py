# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.exceptions import UserError
from odoo.fields import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
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
        employee = self.env['hr.employee'].sudo().create({
            'name': 'Test Employee',
            'company_id': self.company.id,
        })
        self.assertTrue(employee.work_contact_id, "An employee should always have a work contact")

        self.pos_config_usd.write({'module_pos_hr': True})

        # LIMIT 0 always yields zero rows, so any partner in the domain result
        # can only come from pos_hr explicitly forcing it in.
        with patch.object(self.env.registry.models['pos.config'], '_get_limited_partner_count', return_value=0):
            domain = self.env['res.partner']._load_pos_data_domain({'pos.config': self.pos_config_usd, 'pos.order': self.env['pos.order']})
            partners = self.env['res.partner'].search(domain)

        self.assertIn(
            employee.work_contact_id, partners,
            "The work contact of an employee allowed on the config must always be loaded, "
            "regardless of the limited partner loading count",
        )

    def test_cash_in_out_has_no_partner(self):
        employee = self.env['hr.employee'].sudo().create({
            'name': 'Test Employee',
            'company_id': self.company.id,
        })
        self.pos_config_usd.write({'module_pos_hr': True})
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        session.set_opening_control(0, False)
        session.try_cash_in_out('out', 10, 'Deposit', employee.work_contact_id.id, employee_id=employee.id)

        cash_move = session.bank_statement_line_ids
        self.assertFalse(cash_move.partner_id)
        self.assertFalse(cash_move.move_id.line_ids.partner_id)
        self.assertEqual(session.get_cash_in_out_list()[0]['cashier_name'], 'Test Employee')

        session.delete_cash_in_out(cash_move.id, employee.work_contact_id.id)
        self.assertIn('Test Employee: -10.0', session.message_ids[0].body)

    def test_employee_pos_config_cleanup(self):
        """ Test that archiving an employee or changing their company removes them from POS configurations. """
        company_b = self.env['res.company'].sudo().create({'name': 'Company B'})
        employee = self.env['hr.employee'].sudo().create({
            'name': 'Test Cleanup Employee',
            'company_id': self.pos_config_usd.company_id.id,
        })
        self.pos_config_usd.sudo().write({
            'module_pos_hr': True,
            'advanced_employee_ids': [Command.set(employee.ids)],
        })
        self.assertIn(employee, self.pos_config_usd.advanced_employee_ids)
        employee.sudo().write({'active': False})
        self.assertNotIn(employee, self.pos_config_usd.advanced_employee_ids)
        employee.sudo().write({'active': True})
        self.pos_config_usd.sudo().write({
            'advanced_employee_ids': [Command.set(employee.ids)],
        })
        self.assertIn(employee, self.pos_config_usd.advanced_employee_ids)
        employee.sudo().write({'company_id': company_b.id})
        self.assertNotIn(employee, self.pos_config_usd.advanced_employee_ids)
