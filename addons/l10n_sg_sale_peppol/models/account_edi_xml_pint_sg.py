# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountEdiXmlPint_Sg(models.AbstractModel):
    _inherit = 'account.edi.xml.pint_sg'

    def _ubl_add_buyer_reference_node(self, vals):
        # EXTENDS account.edi.xml.pint_sg
        # Return the buyer reference received on the order document (cbc:CustomerReference), which
        # the Peppol order specification requires to be sent back in the invoice.
        super()._ubl_add_buyer_reference_node(vals)

        sale_orders = vals['invoice'].invoice_line_ids.sale_line_ids.order_id
        if len(sale_orders) == 1 and sale_orders.l10n_sg_peppol_order_id and sale_orders.client_order_ref:
            vals['document_node']['cbc:BuyerReference']['_text'] = sale_orders.client_order_ref

    def _ubl_add_order_reference_node(self, vals):
        # EXTENDS account.edi.xml.pint_sg
        # Refer to the order document received over Peppol rather than to the
        # reference manually encoded on the invoice.
        super()._ubl_add_order_reference_node(vals)

        sale_orders = vals['invoice'].invoice_line_ids.sale_line_ids.order_id
        if len(sale_orders) == 1 and sale_orders.l10n_sg_peppol_order_id:
            vals['document_node']['cac:OrderReference']['cbc:ID']['_text'] = sale_orders.l10n_sg_peppol_order_id

    def _ubl_add_invoice_line_node(self, vals):
        # EXTENDS account.edi.xml.pint_sg
        # Link each invoice line back to the line of the order document it originates from.
        super()._ubl_add_invoice_line_node(vals)

        line = vals['line_vals']['base_line']['record']
        if line_item_ref := line.sale_line_ids[:1].l10n_sg_ubl_line_item_ref:
            vals['line_node']['cac:OrderLineReference'] = {
                'cbc:LineID': {'_text': line_item_ref},
            }
