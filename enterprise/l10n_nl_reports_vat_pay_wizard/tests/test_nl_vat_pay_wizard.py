# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNlVatPatWizard(TestAccountReportsCommon):
    def test_modulo_11_checksum(self):
        wizard = self.env['l10n_nl.vat.pay.wizard']
        for communication, checksum in [
            ('2234534622567', '1'),
            ('000056789012345', '5'),
        ]:
            self.assertEqual(wizard._l10n_nl_get_modulo_11_checksum(communication), checksum)

    def test_payment_communication(self):
        self.env.company.vat = 'NL863879123B01'
        self.env.company.account_fiscal_country_id = self.env.ref('base.nl')

        with patch.object(self.env.registry['account.move'], '_get_tax_to_pay_on_closing', lambda move: 100.00):
            for periodicity, date, expected in [
                ('monthly', '2024-03-31', '3863.8791.2140.1030'),
                ('monthly', '2024-07-31', '9863.8791.2140.1070'),
                ('trimester', '2024-03-31', '6863.8791.2140.1210'),
                ('trimester', '2024-04-30', '2863.8791.2140.1220'),
                ('trimester', '2024-05-31', '9863.8791.2140.1230'),
                ('trimester', '2024-06-30', '5863.8791.2140.1240'),
                ('trimester', '2024-09-30', '4863.8791.2140.1270'),
                ('trimester', '2024-12-31', '2863.8791.2140.1300'),
                ('trimester', '2025-01-31', '9863.8791.2140.1310'),
                ('trimester', '2025-02-28', '5863.8791.2140.1320'),
                ('year', '2023-12-31', '3863.8791.2130.1400'),
            ]:
                self.env.company.account_tax_periodicity = periodicity
                closing_move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': fields.Date.from_string(date),
                })
                res = self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('account_reports.mail_activity_type_tax_report_to_pay').id,
                    'res_model_id': self.env['ir.model']._get_id('account.move'),
                    'res_id': closing_move.id,
                }).action_open_tax_activity()
                wizard = self.env[res['res_model']].browse(res['res_id'])
                self.assertEqual(wizard.communication, expected)
