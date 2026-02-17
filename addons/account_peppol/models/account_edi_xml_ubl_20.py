from odoo import models


class AccountEdiXmlUbl_20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _add_document_line_item_nodes(self, line_node, vals):
        super()._add_document_line_item_nodes(line_node, vals)
        invoice = vals.get('invoice')
        if invoice and invoice.peppol_exclude_product_reference:
            if line_node.get('cac:Item').get('cac:SellersItemIdentification'):
                line_node['cac:Item']['cac:SellersItemIdentification'] = None
