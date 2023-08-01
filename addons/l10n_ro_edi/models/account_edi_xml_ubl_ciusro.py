# -*- coding: utf-8 -*-

from odoo import models, _


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

        if partner.country_code == 'RO' and partner.state_id:
            vals["country_subentity"] = 'RO-' + partner.state_id.code

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

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]

            constraints.update({
                f"ciusro_{partner_type}_vat_required": self._check_required_fields(partner, 'vat'),
                f"ciusro_{partner_type}_city_required": self._check_required_fields(partner, 'city'),
                f"ciusro_{partner_type}_street_required": self._check_required_fields(partner, 'street'),
            })

            if partner.country_code == 'RO':
                if not partner.state_id:
                    constraints[f"ciusro_{partner_type}_state_id_required"] = \
                        _("The following partner's state ID is missing: %s") % partner.name

                if partner.state_id and partner.state_id.code == 'B' and partner.city not in SECTOR_RO_CODES:
                    constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                        "The following partner's city name is invalid: %s. "
                        "If partner's state is București, the city name must be 'SECTORX', "
                        "where X is a number between 1-6"
                    ) % partner.name

        return constraints
