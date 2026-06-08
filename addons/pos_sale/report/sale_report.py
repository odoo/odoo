# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.models import TableSQL
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    @api.model
    def _get_done_states(self):
        done_states = super()._get_done_states()
        done_states.extend(['paid', 'invoiced', 'done'])
        return done_states

    state = fields.Selection(
        selection_add=[
            ('paid', 'Paid'),
            ('invoiced', 'Invoiced'),
            ('done', 'Posted'),
        ],
    )

    order_reference = fields.Reference(selection_add=[('pos.order', 'POS Order')])

    @property
    def _table_query(self) -> SQL:
        today = fields.Date.context_today(self)
        query = self.env['pos.order.line'].sudo().with_context(date_to=today)._search(self._pos_order_line_domain())
        query.groupby = SQL(", ").join(self._groupby_pos_list(query.table))
        return SQL(
            "%s UNION ALL %s",
            query.subselect(*self._select_dict_to_list(self._select_pos_dict(query.table))),
            super()._table_query,
        )

    def _pos_order_line_domain(self):
        return Domain('sale_order_line_id', '=', False)

    def _select_pos_dict(self, table: TableSQL):
        order_rate = self._case_value_or_one(table.order_id.currency_rate)
        rate = SQL("%s / %s", table.consolidation_rate, order_rate)
        return {
            'id': SQL("-MIN(%s)", table.id),
            'product_id': SQL("%s", table.product_id),
            'product_uom_id': SQL("%s", table.product_id.uom_id),
            'product_uom_qty': SQL("SUM(%s)", table.qty),
            'qty_delivered': SQL("SUM(%s)", table.qty_delivered),
            'qty_to_deliver': SQL("SUM(%s - %s)", table.qty, table.qty_delivered),
            'qty_invoiced': SQL("CASE WHEN %s IS NOT NULL THEN SUM(%s) ELSE 0 END", table.order_id.account_move, table.qty),
            'qty_to_invoice': SQL("CASE WHEN %s IS NULL THEN SUM(%s) ELSE 0 END", table.order_id.account_move, table.qty),
            'price_unit': SQL("AVG(%s) * %s", table.price_unit, rate),
            'price_total': SQL("SUM(SIGN(%s) * SIGN(%s) * ABS(%s)) * %s", table.qty, table.price_unit, table.price_subtotal_incl, rate),
            'price_subtotal': SQL("SUM(SIGN(%s) * SIGN(%s) * ABS(%s)) * %s", table.qty, table.price_unit, table.price_subtotal, rate),
            'amount_to_invoice': SQL("(CASE WHEN %s IS NULL THEN SUM(%s) ELSE 0 END) * %s", table.order_id.account_move, table.price_subtotal, rate),
            'amount_invoiced': SQL("(CASE WHEN %s IS NOT NULL THEN SUM(%s) ELSE 0 END) * %s", table.order_id.account_move, table.price_subtotal, rate),
            'untaxed_delivered_amount': SQL("CASE WHEN %s IS NOT NULL THEN SUM(%s * %s) ELSE 0 END * %s", table.order_id.account_move, table.price_unit, table.qty_delivered, rate),
            'nbr': SQL("COUNT(*)"),
            'name': table.order_id.name,
            'date': SQL("%s", table.order_id.date_order),
            'state': table.order_id.state,
            'partner_id': table.order_id.partner_id,
            'user_id': table.order_id.user_id,
            'company_id': table.order_id.company_id,
            'categ_id': table.product_id.categ_id,
            'pricelist_id': table.order_id.pricelist_id,
            'team_id': SQL("%s", table.order_id.crm_team_id),
            'product_tmpl_id': table.product_id.product_tmpl_id,
            'commercial_partner_id': table.order_id.partner_id.commercial_partner_id,
            'country_id': table.order_id.partner_id.country_id,
            'industry_id': table.order_id.partner_id.industry_id,
            'state_id': table.order_id.partner_id.state_id,
            'partner_zip': SQL("%s", table.order_id.partner_id.zip),
            'weight': SQL("(SUM(%s) * %s)", table.product_id.weight, table.qty),
            'volume': SQL("(SUM(%s) * %s)", table.product_id.volume, table.qty),
            'discount': table.discount,
            'discount_amount': SQL("SUM((%s * %s * %s / 100.0 * %s))", table.price_unit, table.discount, table.qty, rate),
            'currency_id': SQL("%s", self.env.company.currency_id.id),
            'order_reference': SQL("concat('pos.order', ',', %s)", table.order_id),
        }

    def _groupby_pos_list(self, table: TableSQL):
        groupby = [
            table.order_id,
            table.order_id.id,
            table.product_id,
            table.product_id.id,
            table.price_unit,
            table.discount,
            table.qty,
            table.product_id.product_tmpl_id,
            table.product_id.product_tmpl_id.id,
            table.order_id.partner_id,
            table.order_id.partner_id.id,
            table.product_id.uom_id,
            table.product_id.uom_id.id,
        ]
        if table.consolidation_rate != SQL("1"):
            groupby.append(table.consolidation_rate)
        return groupby
