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

    def _ubl_add_tax_currency_code_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        self._ubl_add_tax_currency_code_node_company_currency(vals)

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_customization_id_node(vals)
        vals['document_node']['cbc:CustomizationID']['_text'] = 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'

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
        company_id = None

        ro_vat = commercial_partner.vat or commercial_partner._get_additional_identifier('RO_VAT')
        if not _has_vat(ro_vat):
            company_id = commercial_partner._get_additional_identifier('RO_EN')
        else:
            company_id = ro_vat

        vals['party_node']['cac:PartyTaxScheme'] = [{
            'cbc:CompanyID': {'_text': company_id},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': 'VAT' if company_id[:2].isalpha() else 'NOT_EU_VAT'},
            },
        }] if company_id else []

    def _ubl_add_accounting_supplier_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_supplier_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        ro_vat = commercial_partner.vat or commercial_partner._get_additional_identifier('RO_VAT')
        if _has_vat(ro_vat):
            # RO legal registration id is the (RO-prefixed) VAT, not the bare CUI/RO_EN.
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': ro_vat,
                    'schemeID': None,
                },
            }]
        else:
            value = commercial_partner._get_additional_identifier('RO_EN')
            if value:
                vals['party_node']['cac:PartyLegalEntity'] = [{
                    'cbc:RegistrationName': {'_text': commercial_partner.name},
                    'cbc:CompanyID': {
                        '_text': value,
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
        company_id = None

        ro_vat = commercial_partner.vat or commercial_partner._get_additional_identifier('RO_VAT')
        if not _has_vat(ro_vat):
            company_id = DEFAULT_VAT
        else:
            company_id = ro_vat

        vals['party_node']['cac:PartyTaxScheme'] = [{
            'cbc:CompanyID': {'_text': company_id},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': 'VAT' if company_id[:2].isalpha() else 'NOT_EU_VAT'},
            },
        }] if company_id else []

    def _ubl_add_accounting_customer_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_accounting_customer_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        ro_vat = commercial_partner.vat or commercial_partner._get_additional_identifier('RO_VAT')
        if _has_vat(ro_vat):
            # RO legal registration id is the (RO-prefixed) VAT, not the bare CUI/RO_EN.
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': ro_vat,
                    'schemeID': None,
                },
            }]
        else:
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': DEFAULT_VAT,
                    'schemeID': None,
                },
            }]

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)

        product = vals['base_line']['product_id']
        line_node['cac:Item']['cac:CommodityClassification'] = {
            'cbc:ItemClassificationCode': {
                '_text': product.cpv_code_id.code,
                'listID': 'STI',
            }
        }

    def _ubl_add_line_item_name_description_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_line_item_name_description_nodes(vals)
        item_node = vals['item_node']

        if name := item_node['cbc:Name'] and item_node['cbc:Name'].get('_text'):
            item_node['cbc:Name']['_text'] = name[:100]
        if description := item_node['cbc:Description'] and item_node['cbc:Description'].get('_text'):
            item_node['cbc:Description']['_text'] = description[:200]

    def _ubl_add_notes_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_notes_nodes(vals)
        document_node = vals['document_node']

        if note := document_node['cbc:Note']['_text']:
            document_node['cbc:Note']['_text'] = note[:300]

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
            and not supplier._get_additional_identifier('RO_EN')
        ):
            constraints["ciusro_supplier_tax_identifier_required"] = _(
                "The following partner doesn't have a VAT nor any other Peppol-routable identifier: %s. "
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
        # ANAF allows for endpoints to be an email address; we don't want to create
        # a partner whose routing endpoint is an email, so drop it in that case.
        if (endpoint := partner_vals.get('routing_identifier')) and '@' in endpoint:
            partner_vals['routing_identifier'] = False
        return partner_vals
