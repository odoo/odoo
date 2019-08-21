# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.tests.common import Form, SavepointCase


CH_POSTAL_ACC_PRETTY = '01-162-8'
CH_POSTAL_ACC_RAW = '010001628'
CH_IBAN = 'CH15 3881 5158 3845 3843 7'
FR_IBAN = 'FR83 8723 4133 8709 9079 4002 530'
CH_POST_IBAN = 'CH09 0900 0000 1000 8060 7'
CH_POSTAL_ACC_FROM_IBAN = '10-8060-7'

class TestBankPostal(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env.ref('base.res_partner_12')
        cls.ch_bank = cls.env['res.bank'].create({
            'name': 'Alternative Bank Schweiz AG',
            'bic': 'ALSWCH21XXX',
            'clearing': '38815',
        })
        cls.post_bank = cls.env['res.bank'].search(
            [('bic', '=', 'POFICHBEXXX')])
        if not cls.post_bank:
            cls.post_bank = cls.env['res.bank'].create({
                'name': 'PostFinance AG',
                'bic': 'POFICHBEXXX',
                'clearing': '9000',
            })

    def new_partner_bank_form(self):
        form = Form(
            self.env['res.partner.bank'],
            view="l10n_ch.isr_partner_bank_form",
        )
        form.partner_id = self.partner
        return form

    def test_onchange_acc_number_postal_pretty(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_POSTAL_ACC_PRETTY
        account = bank_acc.save()

        self.assertEqual(account.l10n_ch_postal, CH_POSTAL_ACC_PRETTY)
        self.assertEqual(account.acc_type, 'postal')

    def test_onchange_acc_number_postal_unformated(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_POSTAL_ACC_RAW
        account = bank_acc.save()

        self.assertEqual(account.l10n_ch_postal, CH_POSTAL_ACC_PRETTY)
        self.assertEqual(account.acc_type, 'postal')

    def test_onchange_acc_number_iban_ch(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_IBAN
        account = bank_acc.save()

        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_iban_ch_postfinance(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_POST_IBAN
        account = bank_acc.save()

        self.assertEqual(account.l10n_ch_postal, CH_POSTAL_ACC_FROM_IBAN)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_iban_foreign(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = FR_IBAN
        account = bank_acc.save()

        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_none(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = 'anything'
        account = bank_acc.save()

        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'bank')
