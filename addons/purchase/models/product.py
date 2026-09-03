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

    def _has_confirmed_purchase(self, company_id=False):
        return bool(self.env['purchase.order.line'].sudo().search_count([
            ('product_id.product_tmpl_id', 'in', self.ids),
            ('order_id.state', '=', 'purchase'),
            ('order_id.date_approve', '!=', False),
            ('order_id.company_id', '=', company_id.id) if company_id
                else ('order_id.company_id', 'in', self.env.companies.ids),
        ], limit=1))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased',
        digits='Product Unit')

    sold_by_vendor_id = fields.Many2one(
        'res.partner', string='Vendor', store=False,
        search='_search_sold_by_vendor',
    )

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
        """ Adds orders not received to forecasted stock tally, """
        res = super()._compute_forecasted_without_stock()
        domain = Domain.AND([
            Domain('order_id.state', '=', 'purchase'),
            Domain('product_id', 'in', self.ids),
            Domain("company_id", "in", self.env.companies.ids),
        ])
        if self.env.context.get("to_date"):
            domain = Domain.AND([
                domain,
                Domain('order_id.date_planned', '<=', self.env.context.get("to_date").date())
            ])
        order_lines = self.env['purchase.order.line'].sudo()._read_group(domain, ['product_id', 'uom_id'], ['product_uom_qty:sum', 'qty_received:sum'])
        for product, line_uom, qty_ordered, qty_received in order_lines:
            to_receive = (qty_ordered - qty_received) * line_uom.factor / product.uom_id.factor
            res[product.id]['incoming_qty'] += to_receive
            res[product.id]['virtual_available'] += to_receive
        return res

    def _search_sold_by_vendor(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        partners = self.env['res.partner'].search([('id', operator, value)])
        partners |= partners.parent_id
        if not partners:
            return Domain.FALSE

        pricelist_ids = set(self.search([
            ('seller_ids.partner_id', 'in', partners.ids),
        ]).ids)

        po_product_ids = set(self.env['purchase.order.line'].sudo().search([
            ('order_id.partner_id', 'child_of', partners.ids),
            ('order_id.state', '=', 'purchase'),
            ('order_id.company_id', 'in', self.env.companies.ids),
        ]).mapped('product_id.id'))

        return [('id', 'in', list(pricelist_ids | po_product_ids))]

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

    def _has_confirmed_purchase(self, company_id=False):
        return bool(self.env['purchase.order.line'].sudo().search_count([
            ('product_id', 'in', self.ids),
            ('order_id.state', '=', 'purchase'),
            ('order_id.date_approve', '!=', False),
            ('order_id.company_id', '=', company_id.id) if company_id
                else ('order_id.company_id', 'in', self.env.companies.ids),
        ], limit=1))

    def _has_vendor_pricelist(self, partner_id=False, company_id=False):
        self.ensure_one()
        partners = partner_id | partner_id.parent_id if partner_id else self.env['res.partner']
        return any(
            (not s.product_id or s.product_id == self)
            and (not s.company_id or not company_id or s.company_id == company_id)
            and (not partners or s.partner_id in partners)
            for s in self.seller_ids
        )

    def _get_last_po_line(self, partner_id=False, company_id=False):
        if not self.id:
            return self.env['purchase.order.line'].sudo()
        domain = [
            ('state', '=', 'purchase'),
            ('date_approve', '!=', False),
            ('order_line.product_id', '=', self.id),
        ]
        if partner_id:
            vendor = partner_id if not partner_id.parent_id else partner_id.parent_id
            domain.append(('partner_id', 'child_of', vendor.id))
        if company_id:
            domain.append(('company_id', '=', company_id.id))
        else:
            domain.append(('company_id', 'in', self.env.companies.ids))
        last_order = self.env['purchase.order'].sudo().search(domain, order='date_approve desc, id desc', limit=1)
        return self.env['purchase.order.line'].sudo().search([
            ('order_id', '=', last_order.id),
            ('product_id', '=', self.id),
        ], order='id desc', limit=1)

    def _get_last_po_seller_info(self, partner_id=False, company_id=False):
        last_line = self._get_last_po_line(partner_id=partner_id, company_id=company_id)
        if not last_line:
            return {}
        last_order = last_line.order_id
        vendor = last_order.partner_id if not last_order.partner_id.parent_id else last_order.partner_id.parent_id
        delay = 0
        if last_line.date_planned and last_order.date_approve:
            delay = max(0, (last_line.date_planned.date() - last_order.date_approve.date()).days)

        return {
            'supplierinfo': self.env['product.supplierinfo'],
            'partner_id': vendor,
            'price': last_line.price_unit,
            'discount': last_line.discount,
            'price_discounted': last_line.uom_id._compute_price(last_line.price_unit_discounted, self.uom_id),
            'currency_id': last_line.currency_id,
            'uom_id': last_line.uom_id,
            'min_qty': 0.0,
            'delay': delay,
        }

    def _is_last_po_fallback_applicable(self, params=False):
        """ Whether the last confirmed po line may act as a vendor pricelist.
            Overridden when the params restrict the sellers to partners that a
            past purchase does not qualify as, e.g. subcontractors.
        """
        return True

    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, ordered_by='price_discounted', params=False):
        seller_info = super()._select_seller(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, ordered_by=ordered_by, params=params)
        if not seller_info and self._is_last_po_fallback_applicable(params):
            company = self.env.company
            if params and params.get('order_id') and params['order_id'].company_id:
                company = params['order_id'].company_id
            if not self._has_vendor_pricelist(partner_id, company):
                # No pricelist defined for this vendor: the last confirmed po line acts as one
                seller_info = self._get_last_po_seller_info(partner_id, company)
        return seller_info


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.company.currency_id.id

    def _get_filtered_supplier(self, company_id, product_id, params=False):
        if params and 'order_id' in params and params['order_id'].company_id:
            company_id = params['order_id'].company_id
        return super()._get_filtered_supplier(company_id, product_id, params)
