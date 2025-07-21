from odoo import models, _
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EAS_MAPPING


CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"
FR_SCHEME_IDS = {v: k for k, v in EAS_MAPPING['FR'].items()}


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    """
    See Pagero documentation: https://www.pagero.com/onboarding/aife/aife-en#requirements
    Chorus Pro documentation: https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/07/Specifications_Externes_Annexe_EDI_V4.22.pdf
    """

    def _export_invoice_vals(self, invoice):
        """
        * Pagero doc states that the siret of the final customer (that has the Chorus peppol ID) should be located in
        the PartyIdentification node.
        * Chorus Pro doc states that french suppliers should mention their siret, and european non-french suppliers
        should put their VAT
        """
        # EXTENDS 'account.edi.xml.ubl_bis3'
        vals = super()._export_invoice_vals(invoice)
        if invoice.buyer_reference:
            # Pagero doc states that the 'Service Code' should be in the BuyerReference node
            vals['vals']['buyer_reference'] = invoice.buyer_reference
        if invoice.purchase_order_reference:
            # Pagero doc states that the 'Commitment Number' should be in the OrderReference/ID node
            vals['vals']['order_reference'] = invoice.purchase_order_reference

        customer = vals['customer'].commercial_partner_id
        if customer.peppol_eas and customer.peppol_endpoint and customer.peppol_eas + ":" + customer.peppol_endpoint == CHORUS_PRO_PEPPOL_ID:
            for role in ('supplier', 'customer'):
                partner = vals[role].commercial_partner_id
                if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR':
                    vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                        'id': partner.siret,
                        'id_attrs': {'schemeID': FR_SCHEME_IDS['siret']},
                    }]
                else:
                    vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                        'id': partner.vat,
                        'id_attrs': {'schemeID': FR_SCHEME_IDS['vat']},
                    }]
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        customer, supplier = vals['customer'].commercial_partner_id, vals['supplier']
        if customer.peppol_eas and customer.peppol_endpoint and customer.peppol_eas + ":" + customer.peppol_endpoint == CHORUS_PRO_PEPPOL_ID:
            if 'siret' not in customer._fields or not customer.siret:
                constraints['chorus_customer'] = _("The siret is mandatory for the customer when invoicing to Chorus Pro.")
            if supplier.country_code == 'FR' and ('siret' not in supplier._fields or not supplier.siret):
                constraints['chorus_supplier'] = _("The siret is mandatory for french suppliers when invoicing to Chorus Pro.")
        return constraints

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']

        if invoice.buyer_reference:
            # Pagero doc states that the 'Service Code' should be in the BuyerReference node
            document_node['cbc:BuyerReference'] = {'_text': invoice.buyer_reference}

        if invoice.purchase_order_reference:
            # Pagero doc states that the 'Commitment Number' should be in the OrderReference/ID node
            document_node['cac:OrderReference'] = {
                'cbc:ID': {'_text': invoice.purchase_order_reference}
            }

    def _get_party_node(self, vals):
        # * Pagero doc states that the siret of the final customer (that has the Chorus peppol ID) should be located in
        # the PartyIdentification node.
        # * Chorus Pro doc states that french suppliers should mention their siret, and european non-french suppliers
        # should put their VAT
        party_node = super()._get_party_node(vals)

        customer = vals['customer'].commercial_partner_id
        partner = vals['partner'].commercial_partner_id

        if (
            customer.peppol_eas and
            customer.peppol_endpoint and
            customer.peppol_eas + ":" + customer.peppol_endpoint == CHORUS_PRO_PEPPOL_ID
        ):
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': (
                        partner.siret
                        if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR'
                        else partner.vat
                    ),
                    'schemeID': (
                        FR_SCHEME_IDS['siret'] if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR' else FR_SCHEME_IDS['vat']
                    ),
                }
            }

        return party_node
