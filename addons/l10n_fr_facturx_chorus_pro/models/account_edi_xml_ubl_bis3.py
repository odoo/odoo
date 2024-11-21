from odoo import models, _


CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


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
        if customer.peppol_eas + ":" + customer.peppol_endpoint == CHORUS_PRO_PEPPOL_ID:
            for role in ('supplier', 'customer'):
                partner = vals[role].commercial_partner_id
                if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR':
                    vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                        'id': partner.siret,
                        'id_attrs': {'schemeName': 1},
                    }]
                else:
                    vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                        'id': partner.vat,
                        'id_attrs': {'schemeName': 2},
                    }]
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        customer, supplier = vals['customer'].commercial_partner_id, vals['supplier']
        if customer.peppol_eas + ":" + customer.peppol_endpoint == CHORUS_PRO_PEPPOL_ID:
            if 'siret' not in customer._fields or not customer.siret:
                constraints['chorus_customer'] = _("The siret is mandatory for the customer when invoicing to Chorus Pro.")
            if supplier.country_code == 'FR' and ('siret' not in supplier._fields or not supplier.siret):
                constraints['chorus_supplier'] = _("The siret is mandatory for french suppliers when invoicing to Chorus Pro.")
        return constraints
