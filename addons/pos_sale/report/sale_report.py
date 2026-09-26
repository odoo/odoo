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

<<<<<<< 23ba3c83639e2e9012ae4f0d5f5ea6879f670666
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
||||||| 3cb8316c82bba0f9c5c404a38baab69da9603808
    def _fill_pos_fields(self, additional_fields):
        """Hook to fill additional fields for the pos_sale.

        :param additional_fields: Dictionary mapping fields with their values
        :type additional_fields: dict[str, Any]
        """
        filled_fields = {x: 'NULL' for x in additional_fields}
        for fname, value in self._available_additional_pos_fields().items():
            if fname in additional_fields:
                filled_fields[fname] = value
        return filled_fields

    def _from_pos(self):
        currency_table = self.env['res.currency']._get_simple_currency_table(self.env.companies)
        return """
            pos_order_line l
            JOIN pos_order pos ON l.order_id = pos.id
            LEFT JOIN res_partner partner ON (pos.partner_id=partner.id OR pos.partner_id = NULL)
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=t.uom_id
            LEFT JOIN pos_session session ON session.id = pos.session_id
            LEFT JOIN pos_config config ON config.id = session.config_id
            JOIN {currency_table} ON account_currency_table.company_id = pos.company_id
            """.format(
            currency_table=self.env.cr.mogrify(currency_table).decode(self.env.cr.connection.encoding),
            )

    def _where_pos(self):
        return """
            l.sale_order_line_id IS NULL"""

    def _group_by_pos(self):
        return """
            l.order_id,
            l.product_id,
            l.price_unit,
            l.discount,
            l.qty,
            t.uom_id,
            t.categ_id,
            pos.id,
            pos.name,
            pos.date_order,
            pos.partner_id,
            pos.user_id,
            pos.state,
            pos.company_id,
            pos.pricelist_id,
            p.product_tmpl_id,
            partner.commercial_partner_id,
            partner.country_id,
            partner.industry_id,
            partner.state_id,
            partner.zip,
            u.factor,
            pos.crm_team_id,
            account_currency_table.rate"""

    def _query(self):
        res = super()._query()
        return res + f"""UNION ALL (
            SELECT {self._select_pos()}
            FROM {self._from_pos()}
            WHERE {self._where_pos()}
            GROUP BY {self._group_by_pos()}
            )
        """
=======
    def _fill_pos_fields(self, additional_fields):
        """Hook to fill additional fields for the pos_sale.

        :param additional_fields: Dictionary mapping fields with their values
        :type additional_fields: dict[str, Any]
        """
        filled_fields = {x: 'NULL' for x in additional_fields}
        for fname, value in self._available_additional_pos_fields().items():
            if fname in additional_fields:
                filled_fields[fname] = value
        return filled_fields

    def _from_pos(self):
        currency_table = self.env['res.currency']._get_simple_currency_table(self.env.companies)
        return """
            pos_order_line l
            JOIN pos_order pos ON l.order_id = pos.id
            LEFT JOIN res_partner partner ON (pos.partner_id=partner.id OR pos.partner_id = NULL)
            LEFT JOIN product_product p ON l.product_id=p.id
            LEFT JOIN product_template t ON p.product_tmpl_id=t.id
            LEFT JOIN uom_uom u ON u.id=t.uom_id
            LEFT JOIN pos_session session ON session.id = pos.session_id
            LEFT JOIN pos_config config ON config.id = session.config_id
            JOIN {currency_table} ON account_currency_table.company_id = pos.company_id
            """.format(
            currency_table=self.env.cr.mogrify(currency_table).decode(self.env.cr.connection.encoding),
            )

    def _where_pos(self):
        return """
            l.sale_order_line_id IS NULL"""

    def _group_by_pos(self):
        return """
            l.order_id,
            l.product_id,
            l.price_unit,
            l.discount,
            l.qty,
            t.uom_id,
            t.categ_id,
            pos.id,
            pos.name,
            pos.date_order,
            pos.partner_id,
            pos.user_id,
            pos.state,
            pos.company_id,
            pos.pricelist_id,
            p.product_tmpl_id,
            partner.commercial_partner_id,
            partner.country_id,
            partner.industry_id,
            partner.state_id,
            partner.zip,
            u.factor,
            pos.crm_team_id,
            account_currency_table.rate"""

    def _query(self):
        res = super()._query()
        return res + f"""UNION ALL (
            SELECT {self._select_pos()}
            FROM {self._from_pos()}
            WHERE {self._where_pos()}
            GROUP BY {self._group_by_pos()}
            )
        """

    def _get_order_reference(self):
        self.ensure_one()
        if self.id < 0:
            line = self.env['pos.order.line'].browse(-self.id)
            line.fetch(['order_id'])
            return line.order_id
        return super()._get_order_reference()
>>>>>>> 1b0631d01c458b54ed154669ae4eeebecaaf6773
