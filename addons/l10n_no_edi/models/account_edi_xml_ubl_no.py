# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLNL(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_no'
    _description = "BIS3 NO (EHF)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _format_no_bronnoysund_number(self, bronnoysund_number):
        if not bronnoysund_number.startswith('NO'):
            bronnoysund_number = 'NO' + bronnoysund_number
        if not bronnoysund_number.endswith('MVA'):
            bronnoysund_number += 'MVA'
        return bronnoysund_number

    def _get_country_vals(self, country):
        # OVERRIDE
        vals = super()._get_country_vals(country)

        vals['identification_code_attrs'] = {'listID': 'ISO3166-1:Alpha2'}

        return vals

    def _get_partner_party_tax_scheme_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_tax_scheme_vals(partner)

        if partner.country_id.code == 'NO':
            vals['company_id'] = self._format_no_bronnoysund_number(partner.l10n_no_bronnoysund_number)

        return vals

    def _get_partner_party_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_vals(partner)

        if partner.country_id.code == 'NO':
            vals['endpoint_id'] = partner.l10n_no_bronnoysund_number
            vals['endpoint_id_attrs'] = {'schemeID': '0192'}

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_no_supplier_endpoint_required': self._check_required_fields(
                vals['supplier'],
                'l10n_no_bronnoysund_number',
            ),
            'bis3_no_commercial_supplier_endpoint_required': self._check_required_fields(
                vals['supplier'].commercial_partner_id,
                'l10n_no_bronnoysund_number',
            ),
        })
        if vals['customer'].country_id.code == 'NO':
            constraints.update({
                'bis3_no_customer_endpoint_required': self._check_required_fields(
                    vals['customer'],
                    'l10n_no_bronnoysund_number',
                ),
                'bis3_no_commercial_customer_endpoint_required': self._check_required_fields(
                    vals['customer'].commercial_partner_id,
                    'l10n_no_bronnoysund_number',
                ),
            })

        return constraints

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_map(self, company):
        # OVERRIDE
        res = super()._import_retrieve_partner_map(company)

        def with_bronnoysund_number(tree, extra_domain):
            endpoint_id_node = tree.find('.//{*}AccountingSupplierParty/{*}Party/{*}EndpointID')

            if endpoint_id_node is None:
                return None

            endpoint_scheme_id = endpoint_id_node.attrib.get('schemeID')
            if endpoint_scheme_id == '0192':
                return self.env['res.partner'].search(extra_domain + [('l10n_no_bronnoysund_number', '=', endpoint_id_node.text)], limit=1)

        res.update({
            21: lambda tree: with_bronnoysund_number(tree, [('company_id', '=', company.id)]),
            22: lambda tree: with_bronnoysund_number(tree, []),
        })
        return res
