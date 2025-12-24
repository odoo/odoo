from odoo import models


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_ro"

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)

        product = vals['base_line']['product_id']
        line_node['cac:Item']['cac:CommodityClassification'] = {
            'cbc:ItemClassificationCode': {
                '_text': product.cpv_code_id.code,
                'listID': 'CPV',
            }
        }
