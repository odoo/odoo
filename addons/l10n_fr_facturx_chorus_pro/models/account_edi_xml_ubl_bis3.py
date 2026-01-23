from odoo import models, _


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    """
    See Pagero documentation: https://www.pagero.com/onboarding/aife/aife-en#requirements
    Chorus Pro documentation: https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/07/Specifications_Externes_Annexe_EDI_V4.22.pdf
    """

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        customer, supplier = vals['customer'].commercial_partner_id, vals['supplier']
        if self._is_customer_behind_chorus_pro(customer):
            if not customer.company_registry:
                constraints['chorus_customer'] = _("The Company Registry (Siret) of the final recipient is mandatory for the customer when invoicing through Chorus Pro.")
            if supplier.country_code == 'FR' and not supplier.company_registry:
                constraints['chorus_supplier_fr'] = _("The Company Registry (Siret) is mandatory for french suppliers when invoicing through Chorus Pro.")
            if supplier.country_code != 'FR' and not supplier.vat:
                constraints['chorus_supplier_not_fr'] = _("The VAT is mandatory for non-french suppliers when invoicing through Chorus Pro.")
        return constraints

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

    def _ubl_add_party_identification_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        # * Pagero doc states that the siret of the final customer (that has the Chorus peppol ID) should be located in
        # the PartyIdentification node.
        # * Chorus Pro doc states that french suppliers should mention their siret, and european non-french suppliers
        # should put their VAT.
        super()._ubl_add_party_identification_nodes(vals)

        customer = vals['customer'].commercial_partner_id
        if not self._is_customer_behind_chorus_pro(customer):
            return

        nodes = vals['party_node']['cac:PartyIdentification'] = []
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        if commercial_partner.country_code == 'FR' and commercial_partner.company_registry:
            nodes.append({
                'cbc:ID': {
                    '_text': commercial_partner.company_registry,
                    'schemeID': '0009',
                },
            })
        elif commercial_partner.vat:
            nodes.append({
                'cbc:ID': {
                    '_text': commercial_partner.vat,
                    'schemeID': None,
                },
            })

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        # * Pagero doc states that the siret of the final customer (that has the Chorus peppol ID) should be located in
        # the PartyIdentification node.
        # * Chorus Pro doc states that french suppliers should mention their siret, and european non-french suppliers
        # should put their VAT.
        super()._ubl_add_party_legal_entity_nodes(vals)
        customer = vals['customer'].commercial_partner_id
        if not self._is_customer_behind_chorus_pro(customer):
            return

        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        if commercial_partner.country_code == 'FR' and commercial_partner.company_registry:
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': commercial_partner.company_registry,
                    'schemeID': '0009',
                },
            }]
