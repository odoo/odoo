# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import Form
from odoo.tests import tagged, users


@tagged('res_partner')
class TestPartner(TestCrmCommon):

    @users('user_sales_leads')
    def test_parent_sync_sales_rep(self):
        """ Test team_id / user_id sync from parent to children if the contact
        is a person. Company children are not updated. """
        contact_company = self.contact_company.with_env(self.env)
        contact_company_1 = self.contact_company_1.with_env(self.env)
        self.assertFalse(contact_company.team_id)
        self.assertFalse(contact_company.user_id)
        self.assertFalse(contact_company_1.team_id)
        self.assertFalse(contact_company_1.user_id)

        child = self.contact_1.with_env(self.env)
        self.assertEqual(child.parent_id, self.contact_company_1)
        self.assertFalse(child.team_id)
        self.assertFalse(child.user_id)

        # update comppany sales rep info
        contact_company.user_id = self.env.uid
        contact_company.team_id = self.sales_team_1.id

        # change child parent: shold update sales rep info
        child.parent_id = contact_company.id
        self.assertEqual(child.user_id, self.env.user)

        # test form tool
        # <field name="team_id" groups="base.group_no_one"/>
        with self.debug_mode():
            partner_form = Form(self.env['res.partner'], 'base.view_partner_form')
        partner_form.parent_id = contact_company
        partner_form.company_type = 'person'
        partner_form.name = 'Hermes Conrad'
        self.assertEqual(partner_form.team_id, self.sales_team_1)
        self.assertEqual(partner_form.user_id, self.env.user)
        partner_form.parent_id = contact_company_1
        self.assertEqual(partner_form.team_id, self.sales_team_1)
        self.assertEqual(partner_form.user_id, self.env.user)

        # test form tool
        # <field name="team_id" groups="base.group_no_one"/>
        with self.debug_mode():
            partner_form = Form(self.env['res.partner'], 'base.view_partner_form')
        # `parent_id` is invisible when `is_company` is True (`company_type == 'company'`)
        # and parent_id is not set
        # So, set a temporary `parent_id` before setting the contact as company
        # to make `parent_id` visible in the interface while being a company
        # <field name="parent_id"
        #     attrs="{
        #         'invisible': [
        #             '|',
        #             '&amp;', ('is_company','=', True),('parent_id', '=', False),
        #             ('company_name', '!=', False),('company_name', '!=', '')
        #         ]
        #     }"
        # />
        partner_form.parent_id = contact_company_1
        partner_form.company_type = 'company'
        partner_form.parent_id = contact_company
        partner_form.name = 'Mom Corp'
        self.assertFalse(partner_form.team_id)
        self.assertFalse(partner_form.user_id)

    def test_contact_calendar(self):

        context = {
            "active_model": "res.partner",
            "active_id": self.contact_1.id,
        }

        event = self.env["calendar.event"].with_context(context).create([
            {
                "name": "Simulates flow: partner's calendar -> open quickcreate -> Save",
                "allday": False,
                "start": "2024-10-24 13:45:00",
                "stop": "2024-10-24 15:45:00",
            }
        ])
        self.assertEqual(event.res_id, self.contact_1.id, "Partner not linked to the event with res_id")

        event2 = self.env["calendar.event"].with_context(context).create([
            {
                "res_id": 0,
                "name": "Simulates flow: partner's calendar -> open quickcreate -> Edit -> Save",
                "start": "2024-10-24 16:45:00",
                "stop": "2024-10-24 18:45:00",
            }
        ])
        self.assertEqual(event2.res_id, self.contact_1.id, "Partner not linked to the event with res_id (default res_id not used)")
