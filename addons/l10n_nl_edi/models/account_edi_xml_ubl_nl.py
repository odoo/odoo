# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLNL(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_nl'
    _description = "BIS3 NL-CIUS"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_partner_party_legal_entity_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_legal_entity_vals(partner)

        vals['company_id_attrs'] = {'schemeID': '0190' if vals['commercial_partner'].l10n_nl_oin else '0106'}

        return vals

    def _get_partner_party_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_vals(partner)

        if partner.country_id.code == 'NL':
            vals['endpoint_id'] = partner.l10n_nl_oin or partner.l10n_nl_kvk
            vals['endpoint_id_attrs'] = {'schemeID': '0190' if partner.l10n_nl_oin else '0106'}

        return vals

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals['vals']['customization_id'] = 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0'

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_nl_supplier_endpoint_required': self._check_required_fields(
                vals['supplier'],
                ['l10n_nl_oin', 'l10n_nl_kvk'],
            ),
            'bis3_nl_commercial_supplier_endpoint_required': self._check_required_fields(
                vals['supplier'].commercial_partner_id,
                ['l10n_nl_oin', 'l10n_nl_kvk'],
            ),
            'bis3_nl_partner_bank_required': self._check_required_fields(
                invoice,
                'partner_bank_id',
            ),
        })
        if vals['customer'].country_id.code == 'NL':
            constraints.update({
                'bis3_nl_customer_endpoint_required': self._check_required_fields(
                    vals['customer'],
                    ['l10n_nl_oin', 'l10n_nl_kvk'],
                ),
                'bis3_nl_commercial_customer_endpoint_required': self._check_required_fields(
                    vals['customer'].commercial_partner_id,
                    ['l10n_nl_oin', 'l10n_nl_kvk'],
                ),
            })

        return constraints

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_map(self, company):
        # OVERRIDE
        res = super()._import_retrieve_partner_map(company)

        def with_oin_kvk(tree, extra_domain):
            endpoint_id_node = tree.find('.//{*}AccountingSupplierParty/{*}Party/{*}EndpointID')

            if endpoint_id_node is None:
                return None

            endpoint_scheme_id = endpoint_id_node.attrib.get('schemeID')
            if endpoint_scheme_id == '0190':
                return self.env['res.partner'].search(extra_domain + [('l10n_nl_oin', '=', endpoint_id_node.text)], limit=1)
            if endpoint_scheme_id == '0106':
                return self.env['res.partner'].search(extra_domain + [('l10n_nl_kvk', '=', endpoint_id_node.text)], limit=1)

        res.update({
            21: lambda tree: with_oin_kvk(tree, [('company_id', '=', company.id)]),
            22: lambda tree: with_oin_kvk(tree, []),
        })
        return res
