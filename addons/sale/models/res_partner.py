# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression

from odoo.addons.base.models.res_partner import WARNING_HELP, WARNING_MESSAGE


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_order_count = fields.Integer(
        string="Sale Order Count",
        groups='sales_team.group_sale_salesman',
        compute='_compute_sale_order_count',
    )
    sale_order_ids = fields.One2many('sale.order', 'partner_id', 'Sales Order')
    sale_warn = fields.Selection(WARNING_MESSAGE, 'Sales Warnings', default='no-message', help=WARNING_HELP)
    sale_warn_msg = fields.Text('Message for Sales Order')

    @api.model
    def _get_sale_order_domain_count(self):
        return []

    def _compute_sale_order_count(self):
        self.sale_order_count = 0
        if not self.env.user._has_group('sales_team.group_sale_salesman'):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        sale_order_groups = self.env['sale.order']._read_group(
            domain=expression.AND([self._get_sale_order_domain_count(), [('partner_id', 'in', all_partners.ids)]]),
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        for partner, count in sale_order_groups:
            while partner:
                if partner.id in self_ids:
                    partner.sale_order_count += count
                partner = partner.parent_id

    def _has_order(self, partner_domain):
        self.ensure_one()
        sale_order = self.env['sale.order'].sudo().search(
            expression.AND([
                partner_domain,
                [
                    ('state', 'in', ('sent', 'sale')),
                ]
            ]),
            limit=1,
        )
        return bool(sale_order)

    def _can_edit_name(self):
        """ Can't edit `name` if there is (non draft) issued SO. """
        return super()._can_edit_name() and not self._has_order(
            [
                ('partner_invoice_id', '=', self.id),
                ('partner_id', '=', self.id),
            ]
        )

    def can_edit_vat(self):
        """ Can't edit `vat` if there is (non draft) issued SO. """
        return super().can_edit_vat() and not self._has_order(
            [('partner_id', 'child_of', self.commercial_partner_id.id)]
        )

    def _compute_credit_to_invoice(self):
        # EXTENDS 'account'
        super()._compute_credit_to_invoice()
        company = self.env.company
        if not company.account_use_credit_limit:
            return

        sale_orders = self.env['sale.order'].search([
            ('company_id', '=', company.id),
            ('partner_id', 'in', self.ids),
            ('order_line', 'any', [('untaxed_amount_to_invoice', '>', 0)]),
            ('state', '=', 'sale'),
        ])
        for (partner, currency), orders in sale_orders.grouped(lambda so: (so.partner_id, so.currency_id)).items():
            amount_to_invoice_sum = sum(orders.mapped('amount_to_invoice'))
            credit_company_currency = currency._convert(
                amount_to_invoice_sum,
                company.currency_id,
                company,
                fields.Date.context_today(self),
            )
            partner.credit_to_invoice += credit_company_currency

    def unlink(self):
        # Unlink draft/cancelled SO so that the partner can be removed from database
        self.env['sale.order'].sudo().search([
            ('state', 'in', ['draft', 'cancel']),
            '|', '|',
            ('partner_id', 'in', self.ids),
            ('partner_invoice_id', 'in', self.ids),
            ('partner_shipping_id', 'in', self.ids),
        ]).unlink()
        return super().unlink()
