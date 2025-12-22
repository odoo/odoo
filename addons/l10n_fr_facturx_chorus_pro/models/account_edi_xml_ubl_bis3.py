from odoo import _, models


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
        customer = vals['customer'].commercial_partner_id
        if not self._is_customer_behind_chorus_pro(customer):
            return vals

        if invoice.buyer_reference:
            # Pagero doc states that the 'Service Code' should be in the BuyerReference node
            vals['vals']['buyer_reference'] = invoice.buyer_reference
        if invoice.purchase_order_reference:
            # Pagero doc states that the 'Commitment Number' should be in the OrderReference/ID node
            vals['vals']['order_reference'] = invoice.purchase_order_reference

        for role in ('supplier', 'customer'):
            partner = vals[role].commercial_partner_id
            if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR':
                vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                    'id': partner.siret,
                    'id_attrs': {'schemeID': '0009'},
                }]
            else:
                vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_identification_vals'] = [{
                    'id': partner.vat,
                }]
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        if not self._is_customer_behind_chorus_pro(partner):
            return vals_list

        for vals in vals_list:
            if 'siret' in partner._fields and partner.siret:
                # Siret of the final receiver is mandatory when invoicing through Chorus Pro.
                # If this condition is not met, it will fail in the constraint check.
                vals.update({
                    'company_id': partner.siret,
                    'company_id_attrs': {'schemeID': '0009'},
                })
        return vals_list

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        customer, supplier = vals['customer'].commercial_partner_id, vals['supplier']
        if self._is_customer_behind_chorus_pro(customer):
            if 'siret' not in customer._fields or not customer.siret:
                constraints['chorus_customer'] = _("The siret of the final recipient is mandatory for the customer when invoicing through Chorus Pro.")
            if supplier.country_code == 'FR' and ('siret' not in supplier._fields or not supplier.siret):
                constraints['chorus_supplier_fr'] = _("The siret is mandatory for french suppliers when invoicing to Chorus Pro.")
            if supplier.country_code != 'FR' and not supplier.vat:
                constraints['chorus_supplier_not_fr'] = _("The VAT is mandatory for non-french suppliers when invoicing to Chorus Pro.")
        return constraints

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        customer = vals['customer'].commercial_partner_id
        if not self._is_customer_behind_chorus_pro(customer):
            return

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
        if not self._is_customer_behind_chorus_pro(customer):
            return party_node

        partner = vals['partner'].commercial_partner_id

        party_node['cac:PartyIdentification'] = {
            'cbc:ID': {
                '_text': (
                    partner.siret
                    if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR'
                    else partner.vat
                ),
                'schemeID': (
                    '0009' if 'siret' in partner._fields and partner.siret and partner.country_code == 'FR' else None
                ),
            },
        }
        if 'siret' in partner._fields and partner.siret:
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': partner.siret,
                'schemeID': '0009',
            }

        return party_node
