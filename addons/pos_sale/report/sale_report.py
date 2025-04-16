# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
            ('done', 'Posted')
        ],
    )

    order_reference = fields.Reference(selection_add=[('pos.order', 'POS Order')])

    def _select_pos(self):
        select_ = f"""
            -MIN(l.id) AS id,
            l.product_id AS product_id,
            NULL AS line_invoice_status,
            t.uom_id AS product_uom_id,
            SUM(l.qty) AS product_uom_qty,
            SUM(l.qty_delivered) AS qty_delivered,
            SUM(l.qty - l.qty_delivered) AS qty_to_deliver,
            CASE WHEN pos.account_move IS NOT NULL THEN SUM(l.qty) ELSE 0 END AS qty_invoiced,
            CASE WHEN pos.account_move IS NULL THEN SUM(l.qty) ELSE 0 END AS qty_to_invoice,
            AVG(l.price_unit)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            AS price_unit,
            SUM(l.price_subtotal_incl)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            AS price_total,
            SUM(l.price_subtotal)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            AS price_subtotal,
            (CASE WHEN pos.account_move IS NULL THEN SUM(l.price_subtotal) ELSE 0 END)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            AS amount_to_invoice,
            (CASE WHEN pos.account_move IS NOT NULL THEN SUM(l.price_subtotal) ELSE 0 END)
                / MIN({self._case_value_or_one('pos.currency_rate')})
                * {self._case_value_or_one('account_currency_table.rate')}
            AS amount_invoiced,
            count(*) AS nbr,
            pos.name AS name,
            pos.date_order AS date,
            (CASE WHEN pos.state = 'done' THEN 'sale' ELSE pos.state END) AS state,
            NULL as invoice_status,
            pos.partner_id AS partner_id,
            pos.user_id AS user_id,
            pos.company_id AS company_id,
            NULL AS campaign_id,
            NULL AS medium_id,
            NULL AS source_id,
            t.categ_id AS categ_id,
            pos.pricelist_id AS pricelist_id,
            pos.crm_team_id AS team_id,
            p.product_tmpl_id,
            partner.commercial_partner_id AS commercial_partner_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            partner.state_id AS state_id,
            partner.zip AS partner_zip,
            (SUM(p.weight) * l.qty) AS weight,
            (SUM(p.volume) * l.qty) AS volume,
            l.discount AS discount,
            SUM((l.price_unit * l.discount * l.qty / 100.0
                / {self._case_value_or_one('pos.currency_rate')}
                * {self._case_value_or_one('account_currency_table.rate')}))
            AS discount_amount,
            {self.env.company.currency_id.id} AS currency_id,
            concat('pos.order', ',', pos.id) AS order_reference"""

        additional_fields = self._select_additional_fields()
        additional_fields_info = self._fill_pos_fields(additional_fields)
        template = """,
            %s AS %s"""
        for fname, value in additional_fields_info.items():
            select_ += template % (value, fname)
        return select_

    def _available_additional_pos_fields(self):
        """Hook to replace the additional fields from sale with the one from pos_sale."""
        return {
            'warehouse_id': 'picking.warehouse_id',
        }

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
            LEFT JOIN stock_picking_type picking ON picking.id = config.picking_type_id
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
            account_currency_table.rate,
            picking.warehouse_id"""

    def _query(self):
        res = super()._query()
        return res + f"""UNION ALL (
            SELECT {self._select_pos()}
            FROM {self._from_pos()}
            WHERE {self._where_pos()}
            GROUP BY {self._group_by_pos()}
            )
        """
