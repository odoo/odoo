# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    is_abandoned_cart = fields.Boolean('Abandoned Cart')

    def _select(self):
        public_partner_id = self.env.ref('base.public_partner').id
        return super(SaleReport, self)._select() + """,
                CASE
                    WHEN
                        s.state = 'draft'
                        and s.team_id = (SELECT id FROM crm_team WHERE team_type = 'website' LIMIT 1)
                        and s.partner_id != %s
                        and s.date_order <= (SELECT now() at time zone 'UTC' - (COALESCE((SELECT value FROM ir_config_parameter WHERE key = 'website_sale.cart_abandoned_delay'), '1') || ' hour')::INTERVAL)
                    THEN
                        True
                    ELSE
                        False
                END AS is_abandoned_cart
        """ % public_partner_id

    def _group_by(self):
        return super(SaleReport, self)._group_by() + ',is_abandoned_cart'
