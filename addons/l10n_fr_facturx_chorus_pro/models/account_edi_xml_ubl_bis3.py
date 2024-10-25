from odoo import models


CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    """ See Pagero documentation: https://www.pagero.com/onboarding/aife/aife-en#requirements """

    def _get_partner_party_identification_vals_list(self, partner):
        """
        Pagero doc states that the 'siret' of the final customer (that has the Chorus peppol ID) should be located in
        the PartyIdentificiation node
        """
        # EXTENDS 'account.edi.xml.ubl_bis3'
        if (
            partner.peppol_eas
            and partner.peppol_endpoint
            and partner.peppol_eas + ":" + partner.peppol_endpoint == CHORUS_PRO_PEPPOL_ID
            and 'siret' in partner._fields
            and partner.siret
        ):
            return [{
                'id': partner.siret,
            }]
        return super()._get_partner_party_identification_vals_list(partner)

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account.edi.xml.ubl_bis3'
        vals = super()._export_invoice_vals(invoice)
        if invoice.buyer_reference:
            # Pagero doc states that the 'Service Code' should be in the BuyerReference node
            vals['vals']['buyer_reference'] = invoice.buyer_reference
        if invoice.purchase_order_reference:
            # Pagero doc states that the 'Commitment Number' should be in the OrderReference/ID node
            vals['vals']['order_reference'] = invoice.purchase_order_reference
        return vals
