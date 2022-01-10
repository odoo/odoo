# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.tests.common import Form, users


class TestLeadToQuotation(crm_common.TestCrmCases):

    def setUp(self):
        super(TestLeadToQuotation, self).setUp()
        self.test_team = self.env['crm.team'].with_user(self.crm_salemanager).create({
            'name': 'Europe Marketing Team',
            'user_id': self.crm_salemanager.id,
            'sequence': 16,
        })
        self.test_team2 = self.env['crm.team'].with_user(self.crm_salemanager).create({
            'name': 'Africa Marketing Team',
            'user_id': False,
            'sequence': 20,
        })
        self.crm_salemanager.team_id = self.test_team.id

        self.partner_void = self.env['res.partner'].create({
            'email': 'partner@other.company.com',
            'name': 'Partner 1',
            'phone': '+32455001122',
            'user_id': False,
            'team_id': False,
        })
        self.partner_wuser = self.env['res.partner'].create({
            'email': 'supplier@other.company.com',
            'name': 'Partner 2',
            'phone': '+32455334455',
            'user_id': self.crm_salesman.id,
            'team_id': self.test_team2.id,
        })

    @users('csm')
    def test_action_new_quotation_from_current(self):
        """ Test salesperson and team propagation to quotation when created from
        leads. Check that if nothing is defined on both customer and lead info comes
        from context. """
        lead_wo_user = self.env['crm.lead'].create({
            'name': 'Lead  No User',
            'partner_id': self.partner_void.id,
            'user_id': False,
        })
        self.assertEqual(lead_wo_user.team_id, self.test_team,
                         'Lead: default team is based on uid even when having no user')
        self.assertFalse(lead_wo_user.user_id)

        # new quotation
        new_action_ctx = lead_wo_user.action_new_quotation().get('context', {})
        self.assertEqual(new_action_ctx['default_team_id'], self.test_team.id)
        self.assertNotIn('default_user_id', new_action_ctx)
        quotation = Form(self.env['sale.order'].with_context(new_action_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.env.user,
            'Quotation should have current user as salesperson as nothing else as default'
        )
        self.assertEqual(
            quotation.team_id, lead_wo_user.team_id,
            'Quotation should have the same sales team as lead'
        )

        # view quotes and create
        sale_quotation_ctx = lead_wo_user.action_view_sale_quotation()['context']
        # self.assertEqual(sale_quotation_ctx['default_team_id'], self.test_team.id)
        # self.assertNotIn('default_user_id', sale_quotation_ctx)
        quotation = Form(self.env['sale.order'].with_context(sale_quotation_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.env.user,
            'Quotation should have current user as salesperson as nothing else as default'
        )
        self.assertEqual(
            quotation.team_id, lead_wo_user.team_id,
            'Quotation should have the same sales team as lead'
        )

    @users('csm')
    def test_action_new_quotation_from_lead(self):
        """ Test salesperson and team propagation to quotation when created from
        leads. Check that if lead has a salesperson, it should be set as quotation
        salesperson if nothing is defined on the partner. """
        lead_wuser = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'partner_id': self.partner_void.id,
            'user_id': self.crm_salesman.id,
            'team_id': self.test_team2.id,
        })

        # new quotation
        new_action_ctx = lead_wuser.action_new_quotation().get('context', {})
        self.assertEqual(new_action_ctx['default_team_id'], self.test_team2.id)
        self.assertEqual(new_action_ctx['default_user_id'], self.crm_salesman.id)
        quotation = Form(self.env['sale.order'].with_context(new_action_ctx)).save()
        self.assertEqual(
            quotation.user_id, lead_wuser.user_id,
            'Quotation should have the same salesperson as lead'
        )
        # self.assertEqual(
        #     quotation.team_id, lead_wuser.team_id,
        #     'Quotation should have the same sales team as lead'
        # )

        # view quotes and create
        sale_quotation_ctx = lead_wuser.action_view_sale_quotation()['context']
        # self.assertEqual(sale_quotation_ctx['default_team_id'], self.test_team2.id)
        # self.assertEqual(sale_quotation_ctx['default_user_id'], self.crm_salesman.id)
        quotation = Form(self.env['sale.order'].with_context(sale_quotation_ctx)).save()
        # self.assertEqual(
        #     quotation.user_id, lead_wuser.user_id,
        #     'Quotation should have the same salesperson as lead'
        # )
        # self.assertEqual(
        #     quotation.team_id, lead_wuser.team_id,
        #     'Quotation should have the same sales team as lead'
        # )

    @users('csm')
    def test_action_new_quotation_from_partner(self):
        """ Test salesperson and team propagation to quotation when created from
        leads. Notably check that contact information wins over lead. """
        lead_wo_user = self.env['crm.lead'].create({
            'name': 'Lead No User',
            'partner_id': self.partner_wuser.id,
            'user_id': False,
        })
        self.assertEqual(lead_wo_user.team_id, self.test_team,
                         'Lead: default team is based on uid even when having no user, alas')
        self.assertFalse(lead_wo_user.user_id)

        # new quotation
        new_action_ctx = lead_wo_user.action_new_quotation()['context']
        self.assertEqual(new_action_ctx['default_team_id'], self.test_team.id)
        self.assertNotIn('default_user_id', new_action_ctx)
        quotation = Form(self.env['sale.order'].with_context(new_action_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.partner_wuser.user_id,
            'Quotation should have salesperson from customer'
        )
        self.assertEqual(
            quotation.team_id, self.partner_wuser.team_id,
            'Quotation should have team from customer'
        )

        # view quotes and create
        sale_quotation_ctx = lead_wo_user.action_view_sale_quotation()['context']
        # self.assertEqual(sale_quotation_ctx['default_team_id'], self.test_team.id)
        # self.assertNotIn('default_user_id', sale_quotation_ctx)
        quotation = Form(self.env['sale.order'].with_context(sale_quotation_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.partner_wuser.user_id,
            'Quotation should have salesperson from customer'
        )
        self.assertEqual(
            quotation.team_id, self.partner_wuser.team_id,
            'Quotation should have team from customer'
        )

        # same check when having info on the lead
        lead_wuser = self.env['crm.lead'].create({
            'name': 'Lead User+Team',
            'partner_id': self.partner_wuser.id,
            'user_id': self.crm_salemanager.id,
            'team_id': self.test_team.id,
        })

        # new q
        new_action_ctx = lead_wuser.action_new_quotation().get('context', {})
        self.assertEqual(new_action_ctx['default_team_id'], self.test_team.id)
        self.assertEqual(new_action_ctx['default_user_id'], self.crm_salemanager.id)
        quotation = Form(self.env['sale.order'].with_context(new_action_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.partner_wuser.user_id,
            'Quotation should have salesperson from customer'
        )
        self.assertEqual(
            quotation.team_id, self.partner_wuser.team_id,
            'Quotation should have team from customer'
        )

        # view quotes and create
        sale_quotation_ctx = lead_wuser.action_view_sale_quotation()['context']
        # self.assertEqual(sale_quotation_ctx['default_team_id'], self.test_team.id)
        # self.assertEqual(sale_quotation_ctx['default_user_id'], self.crm_salemanager.id)
        quotation = Form(self.env['sale.order'].with_context(sale_quotation_ctx)).save()
        self.assertEqual(
            quotation.user_id, self.partner_wuser.user_id,
            'Quotation should have salesperson from customer'
        )
        self.assertEqual(
            quotation.team_id, self.partner_wuser.team_id,
            'Quotation should have team from customer'
        )

    def test_initial_values(self):
        self.assertEqual(
            self.env['crm.team'].with_user(self.crm_salemanager)._get_default_team_id(),
            self.test_team
        )
        self.assertEqual(
            self.env['crm.team'].with_user(self.crm_salesman)._get_default_team_id(),
            self.env.ref('sales_team.team_sales_department')
        )

    @users('csm')
    def test_quotation_from_website(self):
        """ This test exists mainly to try to understand a bit various
        use cases and code from onchange_partner_id / onchange_user_id on
        SO model. This is a complete mess. Tests are not trying to enforce a
        result, more to assert current behavior in 13. Added when 15.1 is
        already out.    """
        # website_sale use case (not_self_saleperson)
        order_ctx = {
            'default_user_id': self.crm_salesman.id,
            'not_self_saleperson': True,
        }
        quotation_form = Form(self.env['sale.order'].with_context(order_ctx))
        quotation_form.team_id = self.env['crm.team']
        quotation_form.user_id = self.env['res.users']
        self.assertFalse(quotation_form.team_id)
        self.assertFalse(quotation_form.user_id)
        # set partner: should avoid setting current user as responsible
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.test_team, 'Currently resetting to current user team.')
        self.assertFalse(quotation_form.user_id)
        # reset some info
        quotation_form.partner_id = self.env['res.partner']
        quotation_form.user_id = self.env.user
        self.assertEqual(quotation_form.team_id, self.test_team)
        self.assertEqual(quotation_form.user_id, self.env.user)
        # set customer again, check team / user impact
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.test_team)
        self.assertEqual(quotation_form.user_id, self.env.user)

        # some classic (and impossible to understand) flows
        order_ctx = {
            'default_user_id': self.crm_salesman.id,
            'not_self_saleperson': False,
        }
        quotation_form = Form(self.env['sale.order'].with_context(order_ctx))
        quotation_form.team_id = self.env['crm.team']
        quotation_form.user_id = self.env['res.users']
        self.assertFalse(quotation_form.team_id)
        self.assertFalse(quotation_form.user_id)
        # set partner
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.env.ref('sales_team.team_sales_department'))
        self.assertEqual(quotation_form.user_id, self.crm_salesman)
        # reset some info
        quotation_form.partner_id = self.env['res.partner']
        quotation_form.user_id = self.env.user
        self.assertEqual(quotation_form.team_id, self.test_team)
        self.assertEqual(quotation_form.user_id, self.env.user)
        # set customer again, check team / user impact
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.env.ref('sales_team.team_sales_department'))
        self.assertEqual(quotation_form.user_id, self.crm_salesman)

        # basic flow
        quotation_form = Form(self.env['sale.order'])
        quotation_form.team_id = self.env['crm.team']
        quotation_form.user_id = self.env['res.users']
        self.assertFalse(quotation_form.team_id)
        self.assertFalse(quotation_form.user_id)
        # set partner
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.env.user.team_id)
        self.assertEqual(quotation_form.user_id, self.env.user)
        # reset some info
        quotation_form.partner_id = self.env['res.partner']
        quotation_form.user_id = self.env.user
        self.assertEqual(quotation_form.team_id, self.test_team)
        self.assertEqual(quotation_form.user_id, self.env.user)
        # set customer again, check team / user impact
        quotation_form.partner_id = self.partner_void
        self.assertEqual(quotation_form.team_id, self.test_team)
        self.assertEqual(quotation_form.user_id, self.env.user)
