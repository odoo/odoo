from odoo import models, api
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


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_filtered_sellers(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        # date = fields.Date.today()
        filtered_sellers = super()._get_filtered_sellers(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params)

        def valid_agreement(seller):
            if not seller.purchase_requisition_id:
                return True
            if quantity and seller.purchase_requisition_line_id.remaining_qty < quantity:
                return False
            if quantity and seller.min_qty > quantity:
                return False
            if not date:
                return True
            start_date = seller.purchase_requisition_id.date_start
            end_date = seller.purchase_requisition_id.date_end
            if start_date and date < start_date:
                return False
            return not (end_date and date > end_date)
        return filtered_sellers.filtered(valid_agreement)
