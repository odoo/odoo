# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBL21(models.AbstractModel):
    _name = "account.edi.xml.ubl_21"
    _inherit = 'account.edi.xml.ubl_20'
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'org.oasis-open:invoice:2.1',
            'credit_note': 'org.oasis-open:creditnote:2.1',
        }

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'PaymentTermsType_template': 'account_edi_ubl_cii.ubl_21_PaymentTermsType',
            'CreditNoteLineType_template': 'account_edi_ubl_cii.ubl_21_CreditNoteLineType',
            'DebitNoteLineType_template': 'account_edi_ubl_cii.ubl_21_DebitNoteLineType',
            'InvoiceType_template': 'account_edi_ubl_cii.ubl_21_InvoiceType',
            'CreditNoteType_template': 'account_edi_ubl_cii.ubl_21_CreditNoteType',
            'DebitNoteType_template': 'account_edi_ubl_cii.ubl_21_DebitNoteType',
        })

        vals['vals'].update({
            'ubl_version_id': 2.1,
            'buyer_reference': invoice.commercial_partner_id.ref,
        })

        return vals
