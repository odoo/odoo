# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)

from odoo.tests import tagged, TransactionCase, Form

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResPartnerBank(SavepointCaseWithUserDemo):
    """Tests account_number
    """

    def test_sanitized_account_number(self):
        partner_bank_model = self.env['res.partner.bank']
        account_number = " BE-001 2518823 03 "
        vals = partner_bank_model.search([('account_number', '=', account_number)])
        self.assertEqual(0, len(vals))
        partner_bank = partner_bank_model.create({
            'account_number': account_number,
            'partner_id': self.env['res.partner'].create({'name': 'Pepper Test'}).id,
        })
        vals = partner_bank_model.search([('account_number', '=', account_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search([('account_number', 'in', [account_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])

        self.assertEqual(partner_bank.account_number, account_number)

        # sanitaze the account_number
        sanitized_account_number = 'BE001251882303'
        self.assertEqual(partner_bank.sanitized_account_number, sanitized_account_number)
        vals = partner_bank_model.search(
            [('account_number', '=', sanitized_account_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search(
            [('account_number', 'in', [sanitized_account_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        self.assertEqual(partner_bank.sanitized_account_number,
                         sanitized_account_number)

        # search is case insensitive
        vals = partner_bank_model.search(
            [('account_number', '=', sanitized_account_number.lower())])
        self.assertEqual(1, len(vals))
        vals = partner_bank_model.search(
            [('account_number', '=', account_number.lower())])
        self.assertEqual(1, len(vals))

        # updating the sanitized value will also update the account_number
        partner_bank.write({'sanitized_account_number': 'BE001251882303WRONG'})
        self.assertEqual(partner_bank.account_number, partner_bank.sanitized_account_number)

    def test_find_or_create_bank_account_create(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        # The bank didn't exist, we should create it
        self.assertRecordValues(found_bank, [{
            'account_number': 'account number',
            'partner_id': partner.id,
            'company_id': False,
            'active': True,
        }])

    def test_find_or_create_bank_account_find_active(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        bank = self.env['res.partner.bank'].create({
            'account_number': 'account number',
            'partner_id': partner.id,
            'company_id': False,
            'active': True,
        })
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        # The bank exists and is active, we should not create a new one
        self.assertEqual(bank, found_bank)

    def test_find_or_create_bank_account_find_inactive(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        self.env['res.partner.bank'].create({
            'account_number': 'account number',
            'partner_id': partner.id,
            'company_id': False,
            'active': False,
        })
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        # The bank exists but is inactive, we should neither create a new one, neither return it
        self.assertFalse(found_bank)

    def test_find_or_create_bank_account_find_parent(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        contact = self.env['res.partner'].create({'name': 'contact', 'parent_id': partner.id})
        partner_bank = self.env['res.partner.bank'].create({
            'account_number': 'account number',
            'partner_id': partner.id,
        })
        # Only the bank on the commercial partner exists
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        self.assertEqual(partner_bank, found_bank)

        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=contact,
            company=self.env.company,
        )
        self.assertEqual(partner_bank, found_bank)

        # Now the bank exists on both partners
        contact_bank = self.env['res.partner.bank'].create({
            'account_number': 'account number',
            'partner_id': contact.id,
        })
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        self.assertEqual(partner_bank, found_bank)

        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=contact,
            company=self.env.company,
        )
        self.assertEqual(contact_bank, found_bank)

        # Only the bank on the contact exists
        partner_bank.unlink()
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        self.assertEqual(contact_bank, found_bank)

        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=contact,
            company=self.env.company,
        )
        self.assertEqual(contact_bank, found_bank)


class TestResPartnerBankForm(TransactionCase):
    def test_create_res_partner_bank(self):
        bank_account_form = Form(
            self.env['res.partner.bank'].with_context(default_partner_id=self.env.user.partner_id.id))
        bank_account_form.account_number = '11234'
        bank_account_form.save()


@tagged('post_install', '-at_install')
class TestResPartnerBankCompanyAccess(TransactionCase):
    """A plain internal user may read their own company's bank accounts
    (res_partner_bank_company_rule), but not the bank accounts of an ordinary
    (non-company) partner."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A plain internal user: only base.group_user, scoped to the test company.
        cls.plain_user = cls.env['res.users'].create({
            'name': 'Plain Internal User',
            'login': 'plain_internal_bank_access',
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, cls.env.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        # A bank owned by the user's own company (its partner is a company).
        cls.company_bank = cls.env['res.partner.bank'].sudo().create({
            'account_number': 'COMPANY-OWNED-0001',
            'partner_id': cls.env.company.partner_id.id,
        })
        # A bank of an ordinary (non-company) partner.
        ordinary_partner = cls.env['res.partner'].sudo().create({
            'name': 'Ordinary Partner',
            'is_company': False,
        })
        cls.ordinary_bank = cls.env['res.partner.bank'].sudo().create({
            'account_number': 'ORDINARY-0001',
            'partner_id': ordinary_partner.id,
        })
        # A bank owned by another company the user is NOT a member of.
        other_company = cls.env['res.company'].create({'name': 'Other Company'})
        cls.other_company_bank = cls.env['res.partner.bank'].sudo().create({
            'account_number': 'OTHER-COMPANY-0001',
            'partner_id': other_company.partner_id.id,
        })

    def test_read_company_bank_account_allowed(self):
        bank = self.company_bank.with_user(self.plain_user)
        self.assertEqual(bank.account_number, 'COMPANY-OWNED-0001')

    def test_read_ordinary_bank_account_denied(self):
        bank = self.ordinary_bank.with_user(self.plain_user)
        self.assertFalse(bank.has_access('read'))

    def test_read_other_company_bank_account_denied(self):
        bank = self.other_company_bank.with_user(self.plain_user)
        self.assertFalse(bank.has_access('read'))
