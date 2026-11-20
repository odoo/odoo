# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import formatLang


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.depends('purchase_requisition_id.name', 'purchase_requisition_line_id.remaining_qty')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('use_simplified_supplier_name'):
            return
        for supplier in self.filtered('purchase_requisition_line_id'):
            supplier.display_name = supplier._add_blanket_order_remaining_label(supplier.display_name)

    @api.model
    def _get_seller_info_display_name(self, seller_info):
        name = super()._get_seller_info_display_name(seller_info)
        supplierinfo = seller_info and seller_info.get('supplierinfo')
        if supplierinfo and supplierinfo.purchase_requisition_line_id:
            name = supplierinfo._add_blanket_order_remaining_label(name)
        return name

    def _add_blanket_order_remaining_label(self, name):
        self.ensure_one()
        label = _(
            "%(agreement)s - %(quantity)s left",
            agreement=self.purchase_requisition_id.name,
            quantity=formatLang(self.env, self.purchase_requisition_line_id.remaining_qty, dp='Product Unit'),
        )
        if name.endswith(')'):
            return f"{name[:-1]} - {label})"
        return f"{name} ({label})"
