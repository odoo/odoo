from odoo import api, models


class AccountEdiXmlUBL21RS(models.AbstractModel):
    _name = "account.edi.xml.ubl.rs"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (RS eFaktura)"

    @api.model
    def _get_customization_ids(self):
        vals = super()._get_customization_ids()
        vals['efaktura_rs'] = 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.rs:srbdt:2022#conformant#urn:mfin.gov.rs:srbdtext:2022'
        return vals

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': self._get_customization_ids()['efaktura_rs'],
            'billing_reference_vals': self._l10n_rs_get_billing_reference(invoice),
        })
        return vals

    def _l10n_rs_get_billing_reference(self, invoice):
        # Billing Reference values for Credit Note
        if invoice.move_type == 'out_refund' and invoice.reversed_entry_id:
            return {
                'id': invoice.reversed_entry_id.name,
                'issue_date': invoice.reversed_entry_id.invoice_date,
            }
        return {}

    def _get_invoice_period_vals_list(self, invoice):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_invoice_period_vals_list(invoice)
        vals_list.append({
            'description_code': '0' if invoice.move_type == 'out_refund' else invoice.l10n_rs_tax_date_obligations_code,
        })
        return vals_list

    def _get_partner_party_vals(self, partner, role):
        vals = super()._get_partner_party_vals(partner, role)
        vat_country, vat_number = partner._split_vat(partner.vat)
        if vat_country.isnumeric():
            vat_number = partner.vat
        vals.update({
            'endpoint_id': vat_number,
            'endpoint_id_attrs': {
                'schemeID': '9948',
            },
        })
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)
        for vals in vals_list:
            vals['company_id'] = partner.l10n_rs_edi_registration_number
        return vals_list

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS 'account_edi_ubl_cii'
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        for vals in vals_list:
            vat_country, vat_number = partner._split_vat(partner.vat)
            if vat_country.isnumeric():
                vat_country = 'RS'
                vat_number = partner.vat
            if vat_country == 'RS' and partner.simple_vat_check(vat_country, vat_number):
                vals['company_id'] = vat_country + vat_number
        return vals_list

    def _get_partner_party_identification_vals_list(self, partner):
        vals_list = super()._get_partner_party_identification_vals_list(partner)
        if partner.country_code == 'RS' and partner.l10n_rs_edi_public_funds:
            vals_list.append({
                'id': f'JBKJS: {partner.l10n_rs_edi_public_funds}',
            })
        return vals_list
