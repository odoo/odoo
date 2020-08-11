# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.tests.common import Form, SavepointCase


CH_ISR_ISSUER = '01-162-8'
CH_IBAN = 'CH15 3881 5158 3845 3843 7'
FR_IBAN = 'FR83 8723 4133 8709 9079 4002 530'
CH_POST_IBAN = 'CH09 0900 0000 1000 8060 7'
CH_POSTAL_ACC = '10-8060-7'


class TestOnchangePostal(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env.ref('base.res_partner_12')
        cls.ch_bank = cls.env['res.bank'].create({
            'name': 'Alternative Bank Schweiz AG',
            'bic': 'ALSWCH21XXX',
        })
        cls.post_bank = cls.env['res.bank'].search(
            [('bic', '=', 'POFICHBEXXX')])
        if not cls.post_bank:
            cls.post_bank = cls.env['res.bank'].create({
                'name': 'PostFinance AG',
                'bic': 'POFICHBEXXX',
            })

    def new_partner_bank_form(self):
        form = Form(
            self.env['res.partner.bank'],
            view="l10n_ch.isr_partner_bank_form",
        )
        form.partner_id = self.partner
        return form

    def test_onchange_acc_number_isr_issuer(self):
        """The user entered ISR issuer number into acc_number

        We detect and move it to l10n_ch_postal.
        It must be moved as it is not unique.
        """
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_ISR_ISSUER
        account = bank_acc.save()

        self.assertEqual(
            account.acc_number,
            "{} {}".format(CH_ISR_ISSUER, self.partner.name)
        )
        self.assertEqual(account.l10n_ch_postal, CH_ISR_ISSUER)
        self.assertEqual(account.acc_type, 'postal')

    def test_onchange_acc_number_postal(self):
        """The user entered postal number into acc_number

        We detect and copy it to l10n_ch_postal.
        """
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_POSTAL_ACC
        account = bank_acc.save()

        self.assertEqual(account.acc_number, CH_POSTAL_ACC)
        self.assertEqual(account.l10n_ch_postal, CH_POSTAL_ACC)
        self.assertEqual(account.acc_type, 'postal')

    def test_onchange_acc_number_iban_ch(self):
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_IBAN
        account = bank_acc.save()

        self.assertEqual(account.acc_number, CH_IBAN)
        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_iban_ch_postfinance(self):
        """The user enter a postal IBAN, postal number can be deduced"""
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = CH_POST_IBAN
        account = bank_acc.save()

        self.assertEqual(account.acc_number, CH_POST_IBAN)
        self.assertEqual(account.l10n_ch_postal, CH_POSTAL_ACC)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_iban_foreign(self):
        """Check IBAN still works changed"""
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = FR_IBAN
        account = bank_acc.save()

        self.assertEqual(account.acc_number, FR_IBAN)
        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'iban')

    def test_onchange_acc_number_none(self):
        """Check misc format still works"""
        bank_acc = self.new_partner_bank_form()
        bank_acc.acc_number = 'anything'
        account = bank_acc.save()

        self.assertEqual(account.acc_number, 'anything')
        self.assertFalse(account.l10n_ch_postal)
        self.assertEqual(account.acc_type, 'bank')
