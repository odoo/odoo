# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestResPartnerBank(SavepointCaseWithUserDemo):
    """Tests acc_number
    """

    def test_sanitized_acc_number(self):
        partner_bank_model = self.env['res.partner.bank']
        acc_number = " BE-001 2518823 03 "
        vals = partner_bank_model.search([('acc_number', '=', acc_number)])
        self.assertEqual(0, len(vals))
        partner_bank = partner_bank_model.create({
            'acc_number': acc_number,
            'partner_id': self.env['res.partner'].create({'name': 'Pepper Test'}).id,
            'acc_type': 'bank',
        })
        vals = partner_bank_model.search([('acc_number', '=', acc_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search([('acc_number', 'in', [acc_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])

        self.assertEqual(partner_bank.acc_number, acc_number)

        # sanitaze the acc_number
        sanitized_acc_number = 'BE001251882303'
        self.assertEqual(partner_bank.sanitized_acc_number, sanitized_acc_number)
        vals = partner_bank_model.search(
            [('acc_number', '=', sanitized_acc_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search(
            [('acc_number', 'in', [sanitized_acc_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        self.assertEqual(partner_bank.sanitized_acc_number,
                         sanitized_acc_number)

        # search is case insensitive
        vals = partner_bank_model.search(
            [('acc_number', '=', sanitized_acc_number.lower())])
        self.assertEqual(1, len(vals))
        vals = partner_bank_model.search(
            [('acc_number', '=', acc_number.lower())])
        self.assertEqual(1, len(vals))

        # updating the sanitized value will also update the acc_number
        partner_bank.write({'sanitized_acc_number': 'BE001251882303WRONG'})
        self.assertEqual(partner_bank.acc_number, partner_bank.sanitized_acc_number)

    def test_find_or_create_bank_account_create(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        found_bank = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number='account number',
            partner=partner,
            company=self.env.company,
        )
        # The bank didn't exist, we should create it
        self.assertRecordValues(found_bank, [{
            'acc_number': 'account number',
            'partner_id': partner.id,
            'company_id': False,
            'active': True,
        }])

    def test_find_or_create_bank_account_find_active(self):
        partner = self.env['res.partner'].create({'name': 'partner name'})
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'account number',
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
            'acc_number': 'account number',
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
            'acc_number': 'account number',
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
            'acc_number': 'account number',
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
