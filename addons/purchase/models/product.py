# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased', digits='Product Unit of Measure')
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", compute='_compute_purchase_method', precompute=True, store=True, readonly=False,
        help="On ordered quantities: Control bills based on ordered quantities.\n"
            "On received quantities: Control bills based on received quantities.")
    purchase_line_warn = fields.Selection(WARNING_MESSAGE, 'Purchase Order Line Warning', help=WARNING_HELP, required=True, default="no-message")
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
            template.purchased_product_qty = float_round(sum(p.purchased_product_qty for
                p in template.product_variant_ids), precision_rounding=template.uom_id.rounding
            )

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('purchase.menu_purchase_root').id]

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('purchase_product_template'):
            return [{
                'label': _('Import Template for Products'),
                'template': '/purchase/static/xls/product_purchase.xls'
            }]
        return res

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = [
            ('state', 'in', ['purchase', 'done']),
            ('product_id', 'in', self.with_context(active_test=False).product_variant_ids.ids),
        ]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased',
        digits='Product Unit of Measure')

    is_in_purchase_order = fields.Boolean(
        compute='_compute_is_in_purchase_order',
        search='_search_is_in_purchase_order',
    )

    def _compute_purchased_product_qty(self):
        date_from = fields.Datetime.to_string(fields.Date.context_today(self) - relativedelta(years=1))
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('product_id', 'in', self.ids),
            ('order_id.date_approve', '>=', date_from)
        ]
        order_lines = self.env['purchase.order.line']._read_group(domain, ['product_id'], ['product_uom_qty:sum'])
        purchased_data = {product.id: qty for product, qty in order_lines}
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = float_round(purchased_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)

    @api.depends_context('order_id')
    def _compute_is_in_purchase_order(self):
        order_id = self.env.context.get('order_id')
        if not order_id:
            self.is_in_purchase_order = False
            return

        read_group_data = self.env['purchase.order.line']._read_group(
            domain=[('order_id', '=', order_id)],
            groupby=['product_id'],
            aggregates=['__count'],
        )
        data = {product.id: count for product, count in read_group_data}
        for product in self:
            product.is_in_purchase_order = bool(data.get(product.id, 0))

    def _search_is_in_purchase_order(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        product_ids = self.env['purchase.order.line'].search([
            ('order_id', 'in', [self.env.context.get('order_id', '')]),
        ]).product_id.ids
        return [('id', 'in', product_ids)]

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', self.ids)]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('purchase.menu_purchase_root').id]


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id

    def _get_filtered_supplier(self, company_id, product_id, params):
        if params and 'order_id' in params and params['order_id'].company_id:
            company_id = params['order_id'].company_id
        return super()._get_filtered_supplier(company_id, product_id, params)

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    purchase = fields.Boolean("Purchase", default=True, help="If true, the packaging can be used for purchase orders")
