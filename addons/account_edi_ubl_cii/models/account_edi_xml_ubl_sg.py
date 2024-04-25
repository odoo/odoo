# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLSG(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.ubl_sg"
    _description = "SG BIS Billing 3.0"

    """
    Documentation: https://www.peppolguide.sg/billing/bis/
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_sg.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'eu.peppol.bis3.sg.ubl:invoice:1.0.3',
            'credit_note': 'eu.peppol.bis3.sg.ubl:creditnote:1.0.3',
        }

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._get_partner_party_vals(partner, role)

        for party_tax_scheme in vals['party_tax_scheme_vals']:
            party_tax_scheme['tax_scheme_vals'] = {'id': 'GST'}

        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        """ https://www.peppolguide.sg/billing/bis/#_payment_means_information
        """
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)
        for vals in vals_list:
            vals.update({
                'payment_means_code': 54,
                'payment_means_code_attrs': {'name': 'Credit Card'},
            })

        return vals_list

    def _get_tax_sg_codes(self, invoice, tax):
        """ https://www.peppolguide.sg/billing/bis/#_gst_category_codes
        """
        tax_category_code = 'SR'
        if tax.amount == 0:
            tax_category_code = 'ZR'
        return tax_category_code

    def _get_tax_category_list(self, invoice, taxes):
        # OVERRIDE
        res = []
        for tax in taxes:
            res.append({
                'id': self._get_tax_sg_codes(invoice, tax),
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'tax_scheme_vals': {'id': 'GST'},
            })
        return res

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': self._get_customization_ids()['ubl_sg'],
        })

        return vals
