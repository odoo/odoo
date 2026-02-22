from odoo import _, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

PDP_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017#compliant#urn:peppol:france:billing:cius:1.0'


class AccountEdiXmlUbl21Fr(models.AbstractModel):
    _name = "account.edi.xml.ubl_21_fr"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "France UBL 2.1 E-Invoicing Format"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21_fr.xml"

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        # Use new helpers
        return self._export_invoice_new(invoice)

    def _export_invoice_constraints_new(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_21
        constraints = super()._export_invoice_constraints_new(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            if not partner.pdp_identifier:
                constraints[f"ubl_21_fr_{partner_type}_pdp_identifier_required"] = _("The following partner's PDP identifier is missing: %s", partner.display_name)
            if not partner.siret:  # TODO: siren also enough
                constraints[f"ubl_21_fr_{partner_type}_siret_required"] = _("The following partner's SIRET is missing: %s", partner.display_name)

        return constraints

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        endpoint_node = tree.find(f'.//cac:{role}Party/cac:Party/cbc:EndpointID', UBL_NAMESPACES)
        if endpoint_node is not None:
            peppol_eas = endpoint_node.attrib.get('schemeID')
            peppol_endpoint = endpoint_node.text
            if peppol_eas and peppol_endpoint:
                # include the EAS and endpoint in the search domain when retrieving the partner
                partner_vals.update({
                    'peppol_eas': peppol_eas,
                    'peppol_endpoint': peppol_endpoint,
                })
            # Note: we can not import `pdp_identifier` because the partner vals are passed to `_import_partner` which
            #       only has a fixed set of kwargs.
            #       We set the value in `_import_fill_invoice`
        return partner_vals

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)

        partner = invoice.partner_id
        if partner.peppol_eas == '0225':
            partner.pdp_identifier = partner.peppol_endpoint

        return logs

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_header_nodes(document_node, vals)
        profile_id = {
            'invoice': 'B1',
            'credit_note': 'S1',
        }.get(vals['document_type'])
        document_node.update({
            'cbc:CustomizationID': {'_text': PDP_CUSTOMIZATION_ID},
            'cbc:ProfileID': {'_text': profile_id},
        })

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_address_vals(partner)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        vals.pop('country_subentity_code', None)
        return vals

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        super()._add_invoice_payment_means_nodes(document_node, vals)
        # [UBL-CR-412]-A UBL invoice should not include the PaymentMeans PaymentDueDate
        document_node['cac:PaymentMeans']['cbc:PaymentDueDate'] = None
        # [UBL-CR-414]-A UBL invoice should not include the PaymentMeans InstructionID
        document_node['cac:PaymentMeans']['cbc:InstructionID'] = None

    def _get_address_node(self, vals):
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        address_node = super()._get_address_node(vals)
        address_node['cbc:CountrySubentityCode'] = None
        address_node['cac:Country']['cbc:Name'] = None
        return address_node

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)

        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        # [UBL-SR-16] Buyer identifier shall occur maximum once
        party_id = commercial_partner.ref
        siret = commercial_partner.siret or ''
        siren = siret[:9]
        party_id = siren
        party_id_scheme = "0231"
        # party_id = siret
        # party_id_scheme = "0009"
        party_node['cac:PartyIdentification'] = {
            'cbc:ID': {'_text': party_id, 'schemeID': party_id_scheme},
        }

        party_node['cbc:EndpointID'] = {
            '_text': commercial_partner.pdp_identifier,
            'schemeID': '0225',
        }

        party_node['cac:PartyTaxScheme'] = [
            {
                'cbc:CompanyID': {'_text': commercial_partner.vat or commercial_partner.pdp_identifier},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT' if commercial_partner.vat else "0225"},
                },
            },
        ]
        party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {'_text': siren, 'schemeID': '0002'}

        party_node['cac:PartyLegalEntity']['cac:RegistrationAddress'] = None

        party_node['cac:Contact']['cbc:ID'] = None
        return party_node
