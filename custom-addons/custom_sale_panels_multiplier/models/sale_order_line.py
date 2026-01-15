# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ========== Fields ==========
    
    product_volume = fields.Float(
        string="Volume",
        related='product_id.volume',
        readonly=True,
        store=False,
        digits='Volume',
        help="Product volume from product template"
    )
    
    number_of_panels = fields.Float(
        string="عدد الألواح",
        digits='Product Unit',
        default=0.0,
        help="عدد الألواح - سيتم ضرب هذه القيمة في الكمية. إذا كان 0 أو فارغ، لن يؤثر على الحسابات."
    )
    
    effective_quantity = fields.Float(
        string="Effective Quantity",
        compute='_compute_effective_quantity',
        store=True,
        digits='Product Unit',
        help="الكمية الفعلية = عدد الألواح × الكمية. إذا كان عدد الألواح = 0، يستخدم الكمية العادية."
    )

    # ========== Compute Methods ==========

    @api.depends('number_of_panels', 'product_uom_qty')
    def _compute_effective_quantity(self):
        """
        حساب الكمية الفعلية بناءً على عدد الألواح × الكمية
        إذا كان number_of_panels = 0 أو فارغ، يستخدم product_uom_qty العادي
        """
        for line in self:
            if line.number_of_panels and line.number_of_panels > 0:
                line.effective_quantity = line.number_of_panels * line.product_uom_qty
            else:
                line.effective_quantity = line.product_uom_qty

    # ========== Override Methods (Safe) ==========

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """
        Override آمن: يستخدم effective_quantity في الحسابات المالية فقط
        إذا كان number_of_panels = 0 أو فارغ، يستخدم product_uom_qty العادي (لا تأثير)
        """
        base_values = super()._prepare_base_line_for_taxes_computation(**kwargs)
        # استخدام effective_quantity فقط إذا كان number_of_panels > 0
        if self.number_of_panels and self.number_of_panels > 0:
            base_values['quantity'] = self.effective_quantity
        # إذا كان number_of_panels = 0 أو فارغ، يستخدم product_uom_qty العادي (لا تأثير)
        return base_values

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids', 'number_of_panels', 'effective_quantity')
    def _compute_amount(self):
        """
        Override آمن: يستخدم effective_quantity في الحسابات فقط
        إذا كان number_of_panels = 0 أو فارغ، يستخدم product_uom_qty العادي
        """
        # استدعاء super أولاً للحصول على الحسابات الأساسية
        super()._compute_amount()
        
        # تعديل الحسابات فقط إذا كان number_of_panels > 0
        lines_to_recompute = self.filtered(lambda l: l.number_of_panels and l.number_of_panels > 0)
        if not lines_to_recompute:
            return
        
        AccountTax = self.env['account.tax']
        for line in lines_to_recompute:
            # إعادة حساب price_subtotal و price_total باستخدام effective_quantity
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line['tax_details']['total_excluded_currency']
            line.price_total = base_line['tax_details']['total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

    def _prepare_invoice_line(self, **optional_values):
        """
        Override آمن: يستخدم effective_quantity في Invoice Line
        إذا كان number_of_panels = 0 أو فارغ، يستخدم product_uom_qty العادي
        """
        res = super()._prepare_invoice_line(**optional_values)
        # استخدام effective_quantity فقط إذا كان number_of_panels > 0
        if self.number_of_panels and self.number_of_panels > 0:
            res['quantity'] = self.effective_quantity
            # إضافة معلومات number_of_panels في الوصف (اختياري)
            if res.get('name'):
                res['name'] = f"{res['name']}\nعدد الألواح: {self.number_of_panels}"
        return res
