# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.tools import formatLang, format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    referrer_id = fields.Many2one('res.partner', 'Referrer', domain=[('grade_id', '!=', False)], tracking=True)
    commission_po_line_id = fields.Many2one('purchase.order.line', 'Referrer Purchase Order line', copy=False)

    def _get_sales_representative(self):
        self.ensure_one()

        # The subscription's Salesperson should be the Purchase Representative.
        sub = self.invoice_line_ids.mapped('subscription_id')[:1]
        sales_rep = sub and sub.user_id or False

        # No subscription: check the sale order's Salesperson.
        if not sales_rep:
            so = self.invoice_line_ids.mapped('sale_line_ids.order_id')[:1]
            sales_rep = so and so.user_id or False

        return sales_rep

    def _get_commission_purchase_order_domain(self):
        self.ensure_one()

        domain = [
            ('partner_id', '=', self.referrer_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'draft'),
            ('currency_id', '=', self.currency_id.id),
            ('purchase_type', '=', 'commission'),
        ]

        sales_rep = self._get_sales_representative()
        if sales_rep:
            domain += [('user_id', '=', sales_rep.id)]

        return domain

    def _get_commission_purchase_order(self):
        self.ensure_one()
        purchase = self.env['purchase.order'].sudo().search(self._get_commission_purchase_order_domain(), limit=1)

        if not purchase:
            sales_rep = self._get_sales_representative()
            purchase = self.env['purchase.order'].with_context(mail_create_nosubscribe=True).sudo().create({
                'partner_id': self.referrer_id.id,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'fiscal_position_id': self.env['account.fiscal.position'].with_company(self.company_id)._get_fiscal_position(self.referrer_id).id,
                'payment_term_id': self.referrer_id.with_company(self.company_id).property_supplier_payment_term_id.id,
                'user_id': sales_rep and sales_rep.id or False,
                'dest_address_id': self.referrer_id.id,
                'origin': self.name,
                'purchase_type': 'commission',
            })

        return purchase

    def _make_commission(self):
        for move in self.filtered(lambda m: m.move_type in ['out_invoice', 'in_invoice', 'out_refund']):
            if move.move_type in ['out_invoice', 'in_invoice']:
                sign = 1
                if move.commission_po_line_id or not move.referrer_id:
                    continue
            else:
                sign = -1
                if not move.commission_po_line_id:
                    continue

            comm_by_rule = defaultdict(float)

            product = None
            order = None
            desc_lines = ""
            for line in move.invoice_line_ids:
                rule = line._get_commission_rule()
                if rule:
                    if not product:
                        product = rule.plan_id.product_id
                    if not order:
                        order = line.subscription_id
                        desc_lines += _("\n%(product)s: from %(start_date)s to %(end_date)s",
                                        product=line.product_id.name,
                                        start_date=format_date(self.env, line.deferred_start_date),
                                        end_date=format_date(self.env, line.deferred_end_date))
                    commission = move.currency_id.round(line.price_subtotal * rule.rate / 100.0)
                    comm_by_rule[rule] += commission

            # regulate commissions
            for r, amount in comm_by_rule.items():
                if r.is_capped:
                    amount = min(amount, r.max_commission)
                    comm_by_rule[r] = amount

            total = sum(comm_by_rule.values())
            if not total:
                continue

            # build description lines
            desc = _(
                'Commission on %(invoice)s, %(partner)s, %(amount)s',
                invoice=move.name,
                partner=move.partner_id.name,
                amount=formatLang(self.env, move.amount_untaxed, currency_obj=move.currency_id),
            )
            if order:
                desc += f"\n{order.name}, {desc_lines}"
                # extend the description to show the number of months to defer the expense over
                end_date_list = move.invoice_line_ids.mapped('deferred_end_date')
                start_date_list = move.invoice_line_ids.mapped('deferred_start_date')
                if any(start_date_list) and any(end_date_list):
                    date_to = max((ed for ed in end_date_list if ed))
                    date_from = min((sd for sd in start_date_list if sd))
                    # we calculate the delta according to the whole range to avoid 11 month and 29 days= 11 months
                    delta = relativedelta(date_to + relativedelta(days=1), date_from)
                    n_months = delta.years * 12 + delta.months + delta.days // 30
                    if n_months:
                        desc += _(' (%d month(s))', n_months)

            purchase = move._get_commission_purchase_order()

            line = self.env['purchase.order.line'].sudo().create({
                'name': desc,
                'product_id': product.id,
                'product_qty': 1,
                'price_unit': total * sign,
                'product_uom': product.uom_id.id,
                'date_planned': fields.Datetime.now(),
                'order_id': purchase.id,
                'qty_received': 1,
            })

            if move.move_type in ['out_invoice', 'in_invoice']:
                # link the purchase order line to the invoice
                move.commission_po_line_id = line
                msg_body = _('New commission. Invoice: %(link)s. Amount: %(amount)s.',
                    link=move._get_html_link(),
                    amount=formatLang(self.env, total, currency_obj=move.currency_id))
            else:
                msg_body = _('Commission refunded. Invoice: %(link)s. Amount: %(amount)s.',
                    link=move._get_html_link(),
                    amount=formatLang(self.env, total, currency_obj=move.currency_id))
            purchase.message_post(body=msg_body)

    def _refund_commission(self):
        return self._make_commission()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'referrer_id': move.referrer_id.id,
                'commission_po_line_id': move.commission_po_line_id.id,
            })
        return super(AccountMove, self)._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def _invoice_paid_hook(self):
        res = super()._invoice_paid_hook()
        self.filtered(lambda move: move.move_type == 'out_refund')._make_commission()
        self.filtered(lambda move: move.move_type == 'out_invoice')._make_commission()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            cpo = self.env['purchase.order'].sudo().search(move._get_commission_purchase_order_domain(), limit=1)
            if cpo and move.move_type == 'out_refund' and cpo.state == 'draft':
                message_body = _("The commission partner order %s must be checked manually (especially refund lines which can be duplicated).", cpo._get_html_link())
                move.message_post(body=message_body)
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_commission_rule(self):
        self.ensure_one()
        template = self.env['sale.order.template']
        sale_order = self.subscription_id or self.sale_line_ids.order_id
        if len(sale_order) == 1:
            template = sale_order.sale_order_template_id
        # check whether the product is part of the subscription template
        template_products = template.sale_order_template_line_ids.product_id.mapped('product_tmpl_id')
        template_id = template.id if template and self.product_id.product_tmpl_id.id in template_products.ids else None
        sub_pricelist = self.subscription_id.pricelist_id
        pricelist_id = sub_pricelist and sub_pricelist.id or self.sale_line_ids.mapped('order_id.pricelist_id')[:1].id

        # In order of precedence, the commission plan can be one of:
        # 1. the commission plan set on the subscription
        # 2. the commission plan set on the sale order
        # 3. the referrer's commission plan
        plan = self.sale_line_ids.order_id.commission_plan_id or self.move_id.referrer_id.commission_plan_id
        if self.subscription_id:
            plan = self.subscription_id.commission_plan_id

        if not plan:
            return self.env['commission.rule']

        return plan._match_rules(self.product_id, template_id, pricelist_id)
