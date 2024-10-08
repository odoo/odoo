from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install", "post_install_l10n")
class TestDocTypes(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='uy'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        service_vat_22 = cls.env["product.product"].create({
            "name": "Virtual Home Staging (VAT 22)",
            "list_price": 38.25,
            "standard_price": 45.5,
            "type": "service",
            "default_code": "VAT 22",
        })

        cls.invoice = cls.env["account.move"].create({
            "partner_id": cls.env["res.partner"].create({"name": "test partner UY"}).id,
            "move_type": "out_invoice",
            "l10n_latam_document_type_id": cls.env.ref("l10n_uy.dc_e_inv_exp").id,
            "invoice_line_ids": [Command.create({
                "product_id": service_vat_22.id,
                "quantity": 1.0,
                "price_unit": 100.0,
            })]
        })
        cls.invoice.action_post()
        cls.partner_CI = cls.env["res.partner"].create({
            "name": "Test partner CI",
            "l10n_latam_identification_type_id": cls.env.ref('l10n_uy.it_ci').id
        })
        cls.partner_RUT = cls.env["res.partner"].create({
            "name": "Test partner RUT",
            "l10n_latam_identification_type_id": cls.env.ref('l10n_uy.it_rut').id
        })

    def test_credit_note(self):
        self.assertEqual(self.invoice.l10n_latam_document_type_id.code, "121", "Not Export e-Invoice")

        refund_wizard = self.env["account.move.reversal"]\
            .with_context({"active_ids": self.invoice.ids, "active_model": "account.move"})\
            .create({
                "reason": "Mercadería defectuosa",
                "journal_id": self.invoice.journal_id.id
            })
        res = refund_wizard.refund_moves()
        refund = self.env["account.move"].browse(res["res_id"])

        self.assertEqual(refund.l10n_latam_document_type_id.code, "122", "Not Export e-Invoice Credit Note")
        expected_docs = ["122"] if self.env['ir.module.module']._get('l10n_uy_edi').state == 'installed' else ['122', '222']
        self.assertEqual(refund.l10n_latam_available_document_type_ids.mapped("code"), expected_docs, "Bad Domain")

    def test_debit_note(self):
        self.assertEqual(self.invoice.l10n_latam_document_type_id.code, "121", "Not Export e-self.invoice")

        debit_note_wizard = self.env["account.debit.note"]\
            .with_context({"active_ids": self.invoice.ids, "active_model": "account.move"})\
            .create({
                "reason": "Mercadería defectuosa",
            })
        res = debit_note_wizard.create_debit()
        debit_note = self.env["account.move"].browse(res["res_id"])

        self.assertEqual(debit_note.l10n_latam_document_type_id.code, "123", "Not Export e-Invoice Debit Note")
        expected_docs = ["123"] if self.env['ir.module.module']._get('l10n_uy_edi').state == 'installed' else ['123', '223']
        self.assertEqual(debit_note.l10n_latam_available_document_type_ids.mapped("code"), expected_docs, "Bad Domain")

    def test_doc_type_byid(self):
        dc_e_ticket = self.env.ref('l10n_uy.dc_e_ticket')
        dc_e_inv = self.env.ref('l10n_uy.dc_e_inv')
        move = self.env['account.move'].create({})
        self.assertFalse(move.l10n_latam_document_type_id)
        move.write({'partner_id': self.partner_CI})
        self.assertEqual(move.l10n_latam_document_type_id, dc_e_ticket, "The document type is not being set correctly.")
        move.write({'partner_id': self.partner_RUT})
        self.assertEqual(move.l10n_latam_document_type_id, dc_e_inv, "The document type is not being set correctly.")
