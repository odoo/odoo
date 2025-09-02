from odoo import models, _


CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    """
    See Pagero documentation: https://www.pagero.com/onboarding/aife/aife-en#requirements
    Chorus Pro documentation: https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/07/Specifications_Externes_Annexe_EDI_V4.22.pdf
    """

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        customer, supplier = vals['customer'].commercial_partner_id, vals['supplier']
        if not customer.identifier_ids.filtered(lambda i: i.iso_identifier == CHORUS_PRO_PEPPOL_ID):
            constraints['chorus_customer'] = _("No partner identification matches Chorus Pro.")
        if supplier.identifier_ids.filtered(lambda i: i.iso_code == '0009'):
            constraints['chorus_supplier'] = _("The SIRET is mandatory for french suppliers when invoicing to Chorus Pro.")
        return constraints

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

        customer = vals['customer'].commercial_partner_id  # FIXME It think there's something wrong in the logic here...
        # partner = vals['partner']
        # commercial_partner = partner.commercial_partner_id

        if (chorus_identification := customer.identifier_ids.filtered(lambda i: i.iso_identifier == CHORUS_PRO_PEPPOL_ID)):
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': chorus_identification.identifier,
                    'schemeID': chorus_identification.iso_code,
                }
            }

        return party_node
