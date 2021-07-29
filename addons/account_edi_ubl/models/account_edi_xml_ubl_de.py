# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLDE(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_de'
    _description = "BIS3 DE (XRechnung)"

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.1#conformant#urn:xoev-de:kosit:extension:xrechnung_2.1',
            'buyer_reference': invoice.commercial_partner_id.name,
        })

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_de_supplier_telephone_required': self._check_required_fields(vals['supplier'], ['phone', 'mobile']),
            'bis3_de_supplier_electronic_mail_required': self._check_required_fields(vals['supplier'], 'email'),
        })

        return constraints
