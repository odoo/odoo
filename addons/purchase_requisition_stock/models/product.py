from odoo import fields, models, api
from odoo.tools import formatLang

class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def _get_seller_info_display_name(self, seller_info):
        if seller_info["supplierinfo"]:
            price_str = formatLang(self.env, seller_info['price'], currency_obj=seller_info['currency_id'])
            return f"{seller_info['partner_id'].display_name} ({seller_info['min_qty']} {seller_info['uom_id'].name} - {price_str}, {seller_info["supplierinfo"].agreement_display_name})"
        return super()._get_seller_info_display_name(seller_info)

    @api.depends('partner_id', 'min_qty', 'uom_id', 'currency_id', 'price')
    @api.depends_context('use_simplified_supplier_name')
    def _compute_display_name(self):
        super()._compute_display_name()
        custom_records = self.filtered(lambda s: s.purchase_requisition_id)
        for supplier in custom_records:
            price_str = formatLang(self.env, supplier.price, currency_obj=supplier.currency_id)
            supplier.display_name = f'{supplier.partner_id.display_name} ({supplier.min_qty} {supplier.uom_id.name} - {price_str}, {supplier.agreement_display_name})'
