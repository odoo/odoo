from odoo import models


class SaleEdiXmlUbl_Bis3_AdvancedOrder(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_advanced_order'
    _inherit = ['sale.edi.xml.ubl_bis3']
    _description = "Sale BIS Advanced Ordering 3.0"

    # -------------------------------------------------------------------------
    # Order EDI Import
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        """ OVERRIDE of `sale_edi_ubl.sale.edi.xml.ubl_bis3` to retrieve advanced order values
            from incoming order documents
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)
        order_change_seq_no = tree.findtext('.//{*}SequenceNumberID')
        if order_change_seq_no is not None:
            order_vals['order_change_seq_no'] = int(order_change_seq_no)

        # For advanced orders, use peppol_order_id as a readonly reference to match documents.
        order_vals['peppol_order_id'] = order_vals.pop('client_order_ref')

        return order_vals, logs

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """Override of `account.edi.common` to adapt dictionary keys from the base method to be
        compatible with the `sale.order.line` model."""
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_item_id = None
        line_item_id_node = tree.find(xpath_dict['line_item_id'])
        if line_item_id_node is not None:
            line_item_id = line_item_id_node.text

        line_vals = {
            'ubl_line_item_ref': line_item_id,
            **super()._retrieve_line_vals(tree, document_type, qty_factor),
        }

        line_status_code = None
        line_status_code_node = tree.find(xpath_dict['line_status_code'])
        if line_status_code_node is not None:
            line_status_code = line_status_code_node.text
            line_vals['line_status_code'] = line_status_code

        return line_vals

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """OVERRIDE of `account.edi.xml.ubl_bis3` to update dictionary key used for extracting
        document line item ID. This is crucial for advanced order to match line items to update on
        order change request.
        """
        if document_type == 'order':
            return {
                **super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor),
                'line_item_id': './{*}ID',
                'line_status_code': './{*}LineStatusCode',
            }
        return super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor)
