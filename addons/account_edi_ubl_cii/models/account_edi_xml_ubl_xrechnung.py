# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLDE(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_de'
    _description = "BIS3 DE (XRechnung)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_de.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'de.xrechnung:ubl-invoice:2.2.0',
            'credit_note': 'de.xrechnung:ubl-creditnote:2.2.0',
        }

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2#conformant#urn:xoev-de:kosit:extension:xrechnung_2.2',
            'buyer_reference': invoice.commercial_partner_id.name,
        })

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_de_supplier_telephone_required': self._check_required_fields(vals['supplier'], ['phone', 'mobile']),
            'bis3_de_supplier_electronic_mail_required': self._check_required_fields(vals['supplier'], 'email'),
        })

        return constraints
