# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'privacy')
class TestPrivacyWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Rintin Tin',
            'email': 'rintin.tin@gmail.com'})

    def test_wizard(self):
        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).create({})

        # Lookup
        wizard.action_lookup()
        self.assertEqual(len(wizard.line_ids), 1)
        self.assertEqual(wizard.line_ids.res_id, self.partner.id)
        self.assertEqual(wizard.line_ids.res_model, self.partner._name)
        self.assertFalse(wizard.log_id)

        # Archive
        wizard.line_ids.is_active = False
        wizard.line_ids._onchange_is_active()
        self.assertFalse(self.partner.active)
        self.assertEqual(wizard.execution_details, 'Archived Contact #%s' % (self.partner.id))
        self.assertTrue(wizard.log_id)
        self.assertEqual(wizard.log_id.anonymized_name, 'R***** T**')
        self.assertEqual(wizard.log_id.anonymized_email, 'r*****.t**@gmail.com')
        self.assertEqual(wizard.log_id.execution_details, 'Archived Contact #%s' % (self.partner.id))
        self.assertEqual(wizard.log_id.records_description, 'Contact (1): #%s' % (self.partner.id))

        # Delete
        wizard.line_ids.action_unlink()
        self.assertEqual(wizard.execution_details, 'Deleted Contact #%s' % (self.partner.id))
        self.assertEqual(wizard.log_id.execution_details, 'Deleted Contact #%s' % (self.partner.id))

    def test_wizard_multi_company(self):
        # Check that the record is spotted, even if not available on the Reference field
        self.env['ir.rule'].create({
            'name': 'Multi-Company Rule',
            'model_id': self.env.ref('base.model_res_partner').id,
            'domain_force': "['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]"
        })
        company_2 = self.env['res.company'].create({'name': 'Company 2'})
        other_partner = self.env['res.partner'].create({
            'name': 'Rintin Tin',
            'email': 'rintin.tin@gmail.com',
            'company_id': company_2.id
        })
        self.assertNotEqual(self.partner.company_id, other_partner.company_id)

        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).with_user(self.env.ref('base.user_admin')).create({})

        # Lookup
        wizard.action_lookup()
        self.assertEqual(len(wizard.line_ids), 2)
        partner_line = wizard.line_ids.filtered(lambda l: l.resource_ref == self.partner)
        self.assertTrue(partner_line)
        self.assertEqual((wizard.line_ids - partner_line).resource_ref, None)

    def test_wizard_direct_reference(self):
        bank = self.env['res.bank'].create({
            'name': 'ING',
            'bic': 'BBRUBEBB',
            'email': 'rintin.tin@gmail.com'
        })

        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).create({})

        # Lookup
        wizard.action_lookup()
        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(wizard.line_ids[0].res_id, self.partner.id)
        self.assertEqual(wizard.line_ids[0].res_model, self.partner._name)

        self.assertEqual(wizard.line_ids[1].res_id, bank.id)
        self.assertEqual(wizard.line_ids[1].res_model, bank._name)

    def test_wizard_indirect_reference(self):
        self.env.company.partner_id = self.partner

        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).create({})

        # Lookup
        wizard.action_lookup()
        self.assertTrue(wizard.line_ids.filtered(lambda l: l.res_model == 'res.partner' and l.res_id == self.partner.id))
        self.assertTrue(wizard.line_ids.filtered(lambda l: l.res_model == 'res.company' and l.res_id == self.env.company.id))

    def test_wizard_indirect_reference_cascade(self):
        # Don't retrieve ondelete cascade records
        self.env["res.partner.bank"].create({
            'acc_number': '0123-%s' % self.partner.id,
            'partner_id': self.partner.id,
            'company_id': self.env.company.id
        })

        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).create({})

        # Lookup
        wizard.action_lookup()
        self.assertEqual(len(wizard.line_ids), 1)
        self.assertEqual(wizard.line_ids[0].res_id, self.partner.id)
        self.assertEqual(wizard.line_ids[0].res_model, self.partner._name)

    def test_wizard_unique_log(self):
        # Check that the log remains unique
        self.env['res.partner'].create({
            'name': 'Rintin Tin',
            'email': 'rintin.tin@gmail.com'})

        wizard = self.env['privacy.lookup.wizard'].with_context(
            default_email=self.partner.email,
            default_name=self.partner.name,
        ).create({})

        # Lookup
        wizard.action_lookup()
        self.assertEqual(len(wizard.line_ids), 2)

        wizard.line_ids[0].is_active = False
        wizard.line_ids[0]._onchange_is_active()
        wizard.execution_details
        self.assertEqual(1, self.env['privacy.log'].search_count([('anonymized_email', '=', 'r*****.t**@gmail.com')]))

        wizard.line_ids[1].is_active = False
        wizard.line_ids[1]._onchange_is_active()
        wizard.execution_details
        self.assertEqual(1, self.env['privacy.log'].search_count([('anonymized_email', '=', 'r*****.t**@gmail.com')]))

    def test_wizard_lookup_with_invalid_email(self):
        # lookup with an invalid email should raise UserError
        wizard = self.env['privacy.lookup.wizard'].create({
            'email': 'demo',
            'name': self.partner.name,
        })
        with self.assertRaises(UserError, msg='Invalid email address "%s"' % wizard.email):
            wizard.action_lookup()
