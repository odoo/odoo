# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.fields import Domain
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased', digits='Product Unit')
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", compute='_compute_purchase_method', precompute=True, store=True, readonly=False,
        help="On ordered quantities: Control bills based on ordered quantities.\n"
            "On received quantities: Control bills based on received quantities.")
    purchase_line_warn_msg = fields.Text('Message for Purchase Order Line')

    @api.depends('type')
    def _compute_purchase_method(self):
        default_purchase_method = self.env['product.template'].default_get(['purchase_method']).get('purchase_method', 'receive')
        for product in self:
            if product.type == 'service':
                product.purchase_method = 'purchase'
            else:
                product.purchase_method = default_purchase_method

    def _compute_purchased_product_qty(self):
        for template in self.with_context(active_test=False):
            template.purchased_product_qty = template.uom_id.round(sum(p.purchased_product_qty for p in template.product_variant_ids))

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('purchase.menu_purchase_root').id]

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('purchase_product_template'):
            return [{
                'label': _('Template for Products'),
                'template': '/purchase/static/xls/products_import_template.xlsx'
            }]
        return res

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = ['&',
            ('state', '=', 'purchase'),
            ('product_id', 'in', self.with_context(active_test=False).product_variant_ids.ids)
        ]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased',
        digits='Product Unit')

    def _compute_purchased_product_qty(self):
        date_from = fields.Datetime.to_string(fields.Date.context_today(self) - relativedelta(years=1))
        domain = [
            ('order_id.state', '=', 'purchase'),
            ('product_id', 'in', self.ids),
            ('order_id.date_approve', '>=', date_from)
        ]
        order_lines = self.env['purchase.order.line']._read_group(domain, ['product_id'], ['product_uom_qty:sum'])
        purchased_data = {product.id: qty for product, qty in order_lines}
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = product.uom_id.round(purchased_data.get(product.id, 0))

    @api.depends_context("to_date")
    def _compute_forecasted_without_stock(self):
        """Add unbilled purchase lines to forecasted stock tally."""
        res = super()._compute_forecasted_without_stock()
        to_date = self.env.context.get("to_date")
        domain = Domain.AND([
            Domain('order_id.state', '=', 'purchase'),
            Domain('product_id', 'in', self.ids),
            Domain("company_id", "in", self.env.companies.ids),
        ])
        if to_date:
            to_date = fields.Datetime.to_datetime(to_date)
            domain = Domain.AND([
                domain,
                Domain('order_id.date_planned', '<=', to_date.date()),
            ])
        order_line_model = self.env['purchase.order.line'].sudo()
        if to_date and to_date.date() < fields.Date.context_today(self):
            order_lines = order_line_model.search(domain).with_context(
                accrual_entry_date=to_date.date()
            )
            for line in order_lines:
                unbilled_qty = line.product_qty - line.qty_invoiced_at_date
                to_bill = line.uom_id._compute_quantity(unbilled_qty, line.product_id.uom_id)
                res[line.product_id.id]['incoming_qty'] += to_bill
                res[line.product_id.id]['virtual_available'] += to_bill
            return res

        order_lines = order_line_model._read_group(
            domain,
            ['product_id', 'uom_id'],
            ['product_qty:sum', 'qty_invoiced:sum'],
        )
        for product, line_uom, qty_ordered, qty_invoiced in order_lines:
            to_bill = line_uom._compute_quantity(
                (qty_ordered or 0.0) - (qty_invoiced or 0.0), product.uom_id
            )
            res[product.id]['incoming_qty'] += to_bill
            res[product.id]['virtual_available'] += to_bill
        return res

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = ['&', ('state', '=', 'purchase'), ('product_id', 'in', self.ids)]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('purchase.menu_purchase_root').id]

    def _update_uom(self, to_uom_id):
        for uom, product, po_lines in self.env['purchase.order.line']._read_group(
            [('product_id', 'in', self.ids)],
            ['uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if uom != product.product_tmpl_id.uom_id:
                raise UserError(_(
                    'As other units of measure (ex : %(problem_uom)s) '
                    'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                    'If you want to change it, please archive the product and create a new one.',
                    problem_uom=uom.display_name, uom=product.product_tmpl_id.uom_id.display_name))
            po_lines.uom_id = to_uom_id
            po_lines.flush_recordset()

        return super()._update_uom(to_uom_id)

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        po_lines = self.env['purchase.order.line'].sudo().search_count(
            [('product_id', 'in', self.ids)], limit=1
        )
        return bool(po_lines)


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id

    def _get_filtered_supplier(self, company_id, product_id, params=False):
        if params and 'order_id' in params and params['order_id'].company_id:
            company_id = params['order_id'].company_id
        return super()._get_filtered_supplier(company_id, product_id, params)
