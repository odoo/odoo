# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.tests.common import tagged
from odoo import Command

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiPa(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Move = cls.env['account.move'].with_company(cls.company)
        journal_code = cls.company_data_2['default_journal_sale'].code
        cls.split_payment_tax = cls.env['account.tax'].with_company(cls.company).search([('name', '=', '22% SP')])
        cls.split_payment_line_data = {
            'name': 'standard_line',
            'quantity': 1,
            'price_unit': 800.40,
            'tax_ids': [Command.set(cls.split_payment_tax.ids)],
        }

        cls.pa_partner_invoice_data = {
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_b.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                Command.create(cls.split_payment_line_data),
            ],
            'l10n_it_origin_document_type': 'purchase_order',
            'l10n_it_origin_document_date': datetime.date(2022, 3, 23),
            'l10n_it_origin_document_name': f"{journal_code}/2022/0001",
            'l10n_it_cup': '0123456789',
            'l10n_it_cig': '0987654321'
        }
        cls.pa_partner_invoice = cls.Move.create(cls.pa_partner_invoice_data)
        cls.pa_partner_invoice_2 = cls.Move.create({
            **cls.pa_partner_invoice_data,
            'l10n_it_origin_document_type': False,
        })
        cls.pa_partner_invoice._post()

    def test_send_pa_partner(self):
        """ ImportoTotaleDocumento must include VAT
            ImportoPagamento must be without VAT
            EsigibilitaIva of the Split payment tax must be 'S'
            The orgin_document fields must appear in the XML.
            Use reference validator: https://fex-app.com/servizi/inizia
        """
        self._assert_export_invoice(self.pa_partner_invoice, 'split_payment.xml')

        credit_note_wizard = self.env['account.move.reversal'] \
            .with_context(active_model='account.move', active_ids=self.pa_partner_invoice.ids) \
            .create({
                'date': datetime.date(2022, 3, 25),
                'journal_id': self.pa_partner_invoice.journal_id.id,
            })
        action = credit_note_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()
        self._assert_export_invoice(credit_note, 'split_payment_cn.xml')
