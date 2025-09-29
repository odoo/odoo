from odoo import api, models, _

CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    """
    See Pagero documentation: https://www.pagero.com/onboarding/aife/aife-en#requirements
    Chorus Pro documentation: https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/07/Specifications_Externes_Annexe_EDI_V4.22.pdf
    """

    @api.model
    def _is_customer_behind_chorus_pro(self, customer):
        return customer.peppol_eas and customer.peppol_endpoint and f"{customer.peppol_eas}:{customer.peppol_endpoint}" == CHORUS_PRO_PEPPOL_ID

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
                    partner.company_registry
                    if partner.company_registry and partner.country_code == 'FR'
                    else partner.vat
                ),
                'schemeID': (
                    '0009' if partner.company_registry and partner.country_code == 'FR' else None
                ),
            },
        }
        if partner.company_registry and partner.country_code == 'FR':
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': partner.company_registry,
                'schemeID': '0009',
            }

        return party_node
