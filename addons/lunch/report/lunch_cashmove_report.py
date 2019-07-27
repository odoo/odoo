# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class CashmoveReport(models.Model):
    _name = "lunch.cashmove.report"
    _description = 'Cashmoves report'
    _auto = False
    _order = "date desc"

    id = fields.Integer('ID')
    amount = fields.Float('Amount')
    date = fields.Date('Date')
    currency_id = fields.Many2one('res.currency', string='Currency')
    user_id = fields.Many2one('res.users', string='User')
    description = fields.Text('Description')

    def name_get(self):
        return [(cashmove.id, '%s %s' % (_('Lunch Cashmove'), '#%d' % cashmove.id)) for cashmove in self]

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)

        self._cr.execute("""
            CREATE or REPLACE view %s as (
                SELECT
                    lc.id as id,
                    lc.amount as amount,
                    lc.date as date,
                    lc.currency_id as currency_id,
                    lc.user_id as user_id,
                    lc.description as description
                FROM lunch_cashmove lc
                UNION ALL
                SELECT
                    -lol.id as id,
                    -lol.price as amount,
                    lol.date as date,
                    lol.currency_id as currency_id,
                    lol.user_id as user_id,
                    format('Order: %%s x %%s %%s', lol.quantity::text, lp.name, lol.display_toppings) as description
                FROM lunch_order lol
                JOIN lunch_product lp ON lp.id = lol.product_id
                WHERE
                    lol.state in ('ordered', 'confirmed')
                    AND lol.active = True
            );
        """ % self._table)
