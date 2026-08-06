from odoo import Command
from odoo.tests import tagged

from .test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRWithholdingReason(TestUBLTRCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chart = cls.env['account.chart.template']
        cls.tax_wh_9_10 = chart.ref('tr_s_wh_20_9_10')
        cls.tax_wh_7_10 = chart.ref('tr_s_wh_20_7_10')
        cls.fpos_wh_9_10 = chart.ref('tr_fp_wh_9_10')
        cls.fpos_wh_7_10 = chart.ref('tr_fp_wh_7_10')
        cls.fpos_wh_3_10 = chart.ref('tr_fp_wh_3_10')
        # 9/10 has ten reasons, 3/10 only one
        cls.reason_607 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_607')
        cls.reason_603 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_603')
        cls.reason_625 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_625')
        # `Update Taxes and Accounts` maps the product's own tax
        cls.product_a.taxes_id = cls.tax_20

    def _draft_invoice(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.einvoice_partner.id,
            'invoice_date': '2025-03-03',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 155.0,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                }),
            ],
        })

    def test_reason_follows_the_line_taxes(self):
        invoice = self._draft_invoice()
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS')

        # picked, not applied: the lines are still on plain VAT
        invoice.fiscal_position_id = self.fpos_wh_9_10
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_20)
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS')
        self.assertFalse(invoice.l10n_tr_available_exemption_code_ids)

        invoice.action_update_fpos_values()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_wh_9_10)
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'TEVKIFAT')
        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.9)
        self.assertIn(self.reason_607.id, invoice.l10n_tr_available_exemption_code_ids)
        invoice.l10n_tr_exemption_code_id = self.reason_607

        # another rate, not applied: the reasons stay on the rate the line has
        invoice.fiscal_position_id = self.fpos_wh_7_10
        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.9)
        self.assertEqual(invoice.l10n_tr_exemption_code_id, self.reason_607)
        self.assertIn(self.reason_607.id, invoice.l10n_tr_available_exemption_code_ids)
        self.assertNotIn(self.reason_603.id, invoice.l10n_tr_available_exemption_code_ids)

        # applied: a 90% reason cannot survive a 7/10 tax
        invoice.action_update_fpos_values()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_wh_7_10)
        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.7)
        self.assertFalse(invoice.l10n_tr_exemption_code_id)
        self.assertIn(self.reason_603.id, invoice.l10n_tr_available_exemption_code_ids)
        self.assertNotIn(self.reason_607.id, invoice.l10n_tr_available_exemption_code_ids)

    def test_withholding_tax_on_the_lines_is_enough(self):
        invoice = self._draft_invoice()
        invoice.invoice_line_ids.tax_ids = self.tax_wh_9_10

        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.9)
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'TEVKIFAT')
        self.assertIn(self.reason_607.id, invoice.l10n_tr_available_exemption_code_ids)

    def test_withholding_return_reads_its_own_lines(self):
        invoice = self._draft_invoice()
        invoice.fiscal_position_id = self.fpos_wh_9_10
        invoice.action_update_fpos_values()
        invoice.l10n_tr_exemption_code_id = self.reason_607
        invoice.action_post()

        credit_note = invoice._reverse_moves()

        self.assertEqual(credit_note.l10n_tr_gib_invoice_type, 'TEVKIFATIADE')
        self.assertEqual(credit_note.l10n_tr_withholding_ratio, 0.9)
        # the reason is inherited; a return's own GİB code comes from the original taxes
        self.assertEqual(credit_note.l10n_tr_exemption_code_id, invoice.l10n_tr_exemption_code_id)
        self.assertFalse(
            self.env['account.move.send']._l10n_tr_withholding_is_inconsistent(credit_note),
        )

    def test_sole_reason_for_the_ratio_is_preselected(self):
        invoice = self._draft_invoice()
        invoice.fiscal_position_id = self.fpos_wh_3_10
        invoice.action_update_fpos_values()

        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.3)
        self.assertEqual(invoice.l10n_tr_available_exemption_code_ids, self.reason_625.ids)
        self.assertEqual(invoice.l10n_tr_exemption_code_id, self.reason_625)

    def test_reason_survives_an_unrelated_line_change(self):
        invoice = self._draft_invoice()
        invoice.fiscal_position_id = self.fpos_wh_9_10
        invoice.action_update_fpos_values()
        invoice.l10n_tr_exemption_code_id = self.reason_607

        invoice.invoice_line_ids = [
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 40.0,
                'tax_ids': [Command.set(self.tax_wh_9_10.ids)],
            }),
        ]

        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.9)
        self.assertEqual(invoice.l10n_tr_exemption_code_id, self.reason_607)

    def test_lines_withholding_at_two_ratios_report_no_ratio(self):
        invoice = self._draft_invoice()
        invoice.invoice_line_ids.tax_ids = self.tax_wh_9_10
        invoice.invoice_line_ids = [
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 40.0,
                'tax_ids': [Command.set(self.tax_wh_7_10.ids)],
            }),
        ]

        self.assertFalse(invoice.l10n_tr_withholding_ratio)
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS')
        self.assertFalse(invoice.l10n_tr_available_exemption_code_ids)
