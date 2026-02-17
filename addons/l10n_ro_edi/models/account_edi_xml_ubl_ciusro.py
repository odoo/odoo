# -*- coding: utf-8 -*-

from odoo import models, _

DEFAULT_VAT = '0000000000000'
SECTOR_RO_CODES = ('SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6')


def get_formatted_sector_ro(city: str):
    return city.upper().replace(' ', '')


def _has_vat(vat):
    return bool(vat and len(vat) > 1)


class AccountEdiXmlUbl_Ro(models.AbstractModel):
    _name = 'account.edi.xml.ubl_ro'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_document_type_code_node(self, invoice, invoice_data):
        # [UBL-SR-43] DocumentTypeCode should only show up on a CreditNote XML with the value '50'
        if invoice.move_type == 'out_refund':
            return {'_text': '50'}

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _ubl_add_values_tax_currency_code(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        self._ubl_add_values_tax_currency_code_company_currency(vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {
            '_text': 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'
        }

    def _ubl_get_partner_address_node(self, vals, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        node = super()._ubl_get_partner_address_node(vals, partner)

        if not partner.state_id:
            return node

        node['cbc:CountrySubentity']['_text'] = f'{partner.country_code}-{partner.state_id.code}'

        # Romania requires the CityName to be in the format of "SECTORX" if the address state is in Bucharest.
        if partner.state_id.code == 'B' and partner.city:
            node['cbc:CityName']['_text'] = get_formatted_sector_ro(partner.city)

        return node

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if not _has_vat(commercial_partner.vat):
            if commercial_partner.company_registry:
                vals['party_node']['cac:PartyTaxScheme'] = [{
                    'cbc:CompanyID': {'_text': commercial_partner.company_registry},
                    'cac:TaxScheme': {
                        'cbc:ID': {'_text': 'VAT' if commercial_partner.company_registry[:2].isalpha() else 'NOT_EU_VAT'},
                    },
                }]
            else:
                vals['party_node']['cac:PartyTaxScheme'] = []

    def _ubl_add_accounting_supplier_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_supplier_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if not _has_vat(commercial_partner.vat):
            if commercial_partner.company_registry:
                vals['party_node']['cac:PartyLegalEntity'] = [{
                    'cbc:RegistrationName': {'_text': commercial_partner.name},
                    'cbc:CompanyID': {
                        '_text': commercial_partner.company_registry,
                        'schemeID': None,
                    },
                }]
            else:
                vals['party_node']['cac:PartyLegalEntity'] = []

    def _ubl_add_accounting_customer_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_customer_party_tax_scheme_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if not _has_vat(commercial_partner.vat):
            vals['party_node']['cac:PartyTaxScheme'] = [{
                'cbc:CompanyID': {'_text': DEFAULT_VAT},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT' if commercial_partner.company_registry[:2].isalpha() else 'NOT_EU_VAT'},
                },
            }]

    def _ubl_add_accounting_customer_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_customer_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if not _has_vat(commercial_partner.vat):
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': DEFAULT_VAT,
                    'schemeID': None,
                },
            }]

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE 'account.edi.xml.ubl_bis3': don't apply Peppol rules
        constraints = self.env['account.edi.xml.ubl_20']._export_invoice_constraints(invoice, vals)
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )

        # Default VAT is only allowed for the receiver (customer), not the provider (supplier)
        supplier = vals['supplier'].commercial_partner_id
        if (
            not _has_vat(supplier.vat)
            and not vals['supplier'].commercial_partner_id.company_registry
        ):
            constraints["ciusro_supplier_tax_identifier_required"] = _(
                "The following partner doesn't have a VAT nor Company ID: %s. "
                "At least one of them is required. ",
                vals['supplier'].display_name)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]

            constraints.update({
                f"ciusro_{partner_type}_city_required": self._check_required_fields(partner, 'city'),
                f"ciusro_{partner_type}_street_required": self._check_required_fields(partner, 'street'),
                f"ciusro_{partner_type}_state_id_required": self._check_required_fields(partner, 'state_id'),
            })

            if (partner.country_code == 'RO'
                    and partner.state_id
                    and partner.state_id.code == 'B'
                    and partner.city
                    and get_formatted_sector_ro(partner.city) not in SECTOR_RO_CODES):
                constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                    "The following partner's city name is invalid: %s. "
                    "If partner's state is București, the city name must be 'SECTORX', "
                    "where X is a number between 1-6.",
                    partner.display_name)

        return constraints

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_bis3
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        if 'peppol_endpoint' in partner_vals:
            # ANAF allows for endpoints to be an address mail, since we don't want to create a new
            # user with an address mail as a PEPPOL endpoint, we simply remove it in that case.
            error = self.env['res.partner']._build_error_peppol_endpoint(False, partner_vals['peppol_endpoint'])
            if error:
                partner_vals['peppol_endpoint'] = False
                partner_vals['peppol_eas'] = False
        return partner_vals
