from odoo import models


class AccountEdiXmlUBL21RS(models.AbstractModel):
    _name = "account.edi.xml.ubl.rs"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (RS eFaktura)"

    def _get_customization_id(self, process_type='billing'):
        return 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.rs:srbdt:2022#conformant#urn:mfin.gov.rs:srbdtext:2022'

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS 'account_edi_ubl_cii'
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_id()}

        # Billing Reference values for Credit Note
        if invoice.move_type == 'out_refund' and invoice.reversed_entry_id:
            document_node['cac:BillingReference'] = {
                'cbc:ID': {'_text': invoice.reversed_entry_id.name},
                'cbc:IssueDate': {'_text': invoice.reversed_entry_id.invoice_date},
            }

        document_node['cac:InvoicePeriod'] = [
            document_node.get('cac:InvoicePeriod'),
            {
                'cbc:DescriptionCode': {
                    '_text': '0' if invoice.move_type == 'out_refund' else invoice.l10n_rs_tax_date_obligations_code
                },
            }
        ]

    def _get_party_node(self, vals):
        # EXTENDS 'account_edi_ubl_cii'
        party_node = super()._get_party_node(vals)
        partner = vals['partner']

        vat_country, vat_number = partner._split_vat(partner.vat)
        if vat_country.isnumeric():
            vat_country = 'RS'
            vat_number = partner.vat

        party_node['cbc:EndpointID'] = {
            '_text': vat_number,
            'schemeID': '9948',
        }

        if partner.country_code == 'RS' and partner.l10n_rs_edi_public_funds:
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': f'JBKJS: {partner.l10n_rs_edi_public_funds}',
                },
            }

        if vat_country == 'RS' and partner._check_vat_number(vat_country, vat_number):
            party_node['cac:PartyTaxScheme']['cbc:CompanyID'] = {'_text': vat_country + vat_number}

        party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {'_text': partner.l10n_rs_edi_registration_number}

        return party_node
