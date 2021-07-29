# -*- coding: utf-8 -*-
from odoo import models, _


class AccountEdiXmlUBL21(models.AbstractModel):
    _name = "account.edi.xml.ubl_21"
    _inherit = 'account.edi.xml.ubl_20'
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals['InvoiceType_template'] = 'account_edi_ubl.ubl_21_InvoiceType'
        vals['vals'].update({
            'ubl_version_id': 2.1,
            'buyer_reference': vals['customer'].commercial_partner_id.name,
        })

        return vals
