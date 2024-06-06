# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round
from dateutil.relativedelta import relativedelta


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased', digits='Product Unit of Measure')
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", compute='_compute_purchase_method', default='receive', store=True, readonly=False,
        help="On ordered quantities: Control bills based on ordered quantities.\n"
            "On received quantities: Control bills based on received quantities.")
    purchase_line_warn = fields.Selection(WARNING_MESSAGE, 'Purchase Order Line Warning', help=WARNING_HELP, required=True, default="no-message")
    purchase_line_warn_msg = fields.Text('Message for Purchase Order Line')

    @api.depends('detailed_type')
    def _compute_purchase_method(self):
        default_purchase_method = self.env['product.template'].default_get(['purchase_method']).get('purchase_method')
        for product in self:
            if product.detailed_type == 'service':
                product.purchase_method = 'purchase'
            else:
                product.purchase_method = default_purchase_method

    def _compute_purchased_product_qty(self):
        for template in self:
            template.purchased_product_qty = float_round(sum([p.purchased_product_qty for p in template.product_variant_ids]), precision_rounding=template.uom_id.rounding)

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
        action['domain'] = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', self.product_variant_ids.ids)]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased',
        digits='Product Unit of Measure')

    def _compute_purchased_product_qty(self):
        date_from = fields.Datetime.to_string(fields.Date.context_today(self) - relativedelta(years=1))
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('product_id', 'in', self.ids),
            ('order_id.date_approve', '>=', date_from)
        ]
        order_lines = self.env['purchase.order.line']._read_group(domain, ['product_id', 'product_uom_qty'], ['product_id'])
        purchased_data = dict([(data['product_id'][0], data['product_uom_qty']) for data in order_lines])
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = float_round(purchased_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)

    def action_view_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.action_purchase_history")
        action['domain'] = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', self.ids)]
        action['display_name'] = _("Purchase History for %s", self.display_name)
        return action


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    purchase = fields.Boolean("Purchase", default=True, help="If true, the packaging can be used for purchase orders")
