# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


SECTOR_RO_CODES = ['SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6']


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.ubl_ro"
    _description = "CIUS RO"

    def _convert_to_ron(self, invoice, amount):
        from_currency = invoice.currency_id
        to_currency = self.env.ref("base.RON")
        converted_amount = from_currency._convert(amount, to_currency, invoice.company_id, invoice.date, False)
        return converted_amount

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._get_partner_address_vals(partner)

        if partner.country_code == 'RO':
            if not partner.state_id:
                # TODO - if partner country is 'RO', they must have state_id
                raise ValidationError("if country is RO, partner must have a state_id")

            vals["country_subentity"] = 'RO-' + partner.state_id.code

            # TODO if state_id is selected as București (RO), the city name must be SECTOR[1-6]
            # make it a selection field later
            if partner.state_id.code == 'B' and partner.city not in SECTOR_RO_CODES:
                raise ValidationError("if state is București, city must be 'SECTORX', where X is a number between 1-6")

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        if invoice.currency_id.name != 'RON':
            vals_list.append({
                'currency': self.env.ref("base.RON"),
                'currency_dp': self.env.ref("base.RON").decimal_places,
                'tax_amount': self._convert_to_ron(invoice, vals_list[0]['tax_amount']),
            })

        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'InvoiceType_template': 'l10n_ro_edi.cius_ro_InvoiceType',
        })

        vals['vals']['customization_id'] = 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'
        vals['vals']['tax_currency_code'] = 'RON'

        return vals
