# -*- coding: utf-8 -*-

from odoo import models, _


SECTOR_RO_CODES = ('SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6')


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.ubl_ro"
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._get_partner_address_vals(partner)

        if partner.state_id:
            vals["country_subentity"] = partner.country_code + '-' + partner.state_id.code

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        if invoice.currency_id.name != 'RON':
            ron_currency = self.env.ref("base.RON")
            vals_list.append({
                'currency': ron_currency,
                'currency_dp': ron_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
            })

        return vals_list

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        if not partner.vat and partner.company_registry:
            # Use company_registry (Company ID) as the VAT replacement
            vals_list = [{'company_id': partner.company_registry, 'tax_scheme_vals': {'id': 'VAT'}}]

        # The validator for CIUS-RO (which extends the validations from the BIS3 Schematron) asserts a rule where:
        # [BR-CO-09] if the PartyTaxScheme/TaxScheme/ID == 'VAT', CompanyID must start with a country code prefix.
        # In Romania however, the CompanyID can be with or without country code prefix and still be perfectly valid.
        # We have to handle their cases by changing the TaxScheme/ID to 'something other than VAT',
        # preventing the trigger of the rule and allow Romanian companies without prefixed VAT to use CIUS-RO.
        for vals in vals_list:
            if partner.country_code == 'RO' and not vals['company_id'].upper().startswith('RO'):
                vals['tax_scheme_vals']['id'] = 'NO_VAT'

        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        for vals in vals_list:
            if not partner.vat and partner.company_registry:
                vals['company_id'] = partner.company_registry

        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1',
            'tax_currency_code': 'RON',
        })

        return vals

    def _get_document_type_code_vals(self, invoice, invoice_data):
        # EXTENDS 'account_edi_ubl_cii
        vals = super()._get_document_type_code_vals(invoice, invoice_data)
        # [UBL-SR-43] DocumentTypeCode should only show up on a CreditNote XML with the value '50'
        vals['value'] = '50' if invoice.move_type == 'out_refund' else False
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii'
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]

            constraints.update({
                f"ciusro_{partner_type}_city_required": self._check_required_fields(partner, 'city'),
                f"ciusro_{partner_type}_street_required": self._check_required_fields(partner, 'street'),
                f"ciusro_{partner_type}_state_id_required": self._check_required_fields(partner, 'state_id'),
            })

            if not partner.commercial_partner_id.vat and not partner.commercial_partner_id.company_registry:
                constraints[f"ciusro_{partner_type}_tax_identifier_required"] = _(
                    "The following partner doesn't have a VAT nor Company ID: %s. "
                    "At least one of them is required. ",
                    partner.display_name)

            if (partner.country_code == 'RO'
                    and partner.state_id
                    and partner.state_id.code == 'B'
                    and partner.city not in SECTOR_RO_CODES):
                constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                    "The following partner's city name is invalid: %s. "
                    "If partner's state is București, the city name must be 'SECTORX', "
                    "where X is a number between 1-6.",
                    partner.display_name)

        return constraints
