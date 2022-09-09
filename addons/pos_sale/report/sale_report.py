# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    @api.model
    def _get_done_states(self):
        done_states = super(SaleReport, self)._get_done_states()
        done_states.extend(['pos_done', 'invoiced'])
        return done_states

    state = fields.Selection(selection_add=[('pos_draft', 'New'),
                                            ('paid', 'Paid'),
                                            ('pos_done', 'Posted'),
                                            ('invoiced', 'Invoiced')], string='Status', readonly=True)

    def _select_pos(self, fields=None):
        if not fields:
            fields = {}
        select_ = '''
            -MIN(l.id) AS id,
            l.product_id AS product_id,
            t.uom_id AS product_uom,
            sum(l.qty) AS product_uom_qty,
            sum(l.qty) AS qty_delivered,
            0 as qty_to_deliver,
            CASE WHEN pos.state = 'invoiced' THEN sum(l.qty) ELSE 0 END AS qty_invoiced,
            CASE WHEN pos.state != 'invoiced' THEN sum(l.qty) ELSE 0 END AS qty_to_invoice,
            SUM(l.price_subtotal_incl) / MIN(CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS price_total,
            SUM(l.price_subtotal) / MIN(CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS price_subtotal,
            (CASE WHEN pos.state != 'invoiced' THEN SUM(l.price_subtotal) ELSE 0 END) / MIN(CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS amount_to_invoice,
            (CASE WHEN pos.state = 'invoiced' THEN SUM(l.price_subtotal) ELSE 0 END) / MIN(CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END) AS amount_invoiced,
            count(*) AS nbr,
            pos.name AS name,
            pos.date_order AS date,
            CASE WHEN pos.state = 'draft' THEN 'pos_draft' WHEN pos.state = 'done' THEN 'pos_done' else pos.state END AS state,
            pos.partner_id AS partner_id,
            pos.user_id AS user_id,
            pos.company_id AS company_id,
            NULL AS campaign_id,
            NULL AS medium_id,
            NULL AS source_id,
            extract(epoch from avg(date_trunc('day',pos.date_order)-date_trunc('day',pos.create_date)))/(24*60*60)::decimal(16,2) AS delay,
            t.categ_id AS categ_id,
            pos.pricelist_id AS pricelist_id,
            NULL AS analytic_account_id,
            pos.crm_team_id AS team_id,
            p.product_tmpl_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            partner.commercial_partner_id AS commercial_partner_id,
            (sum(p.weight) * l.qty / u.factor) AS weight,
            (sum(p.volume) * l.qty / u.factor) AS volume,
            l.discount as discount,
            sum((l.price_unit * l.discount * l.qty / 100.0 / CASE COALESCE(pos.currency_rate, 0) WHEN 0 THEN 1.0 ELSE pos.currency_rate END)) as discount_amount,
            NULL as order_id
        '''

        for field in fields.keys():
            select_ += ', NULL AS %s' % (field)
        return select_

    def _from_pos(self):
        from_ = '''
            pos_order_line l
                  join pos_order pos on (l.order_id=pos.id)
                  left join res_partner partner ON (pos.partner_id = partner.id OR pos.partner_id = NULL)
                    left join product_product p on (l.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    LEFT JOIN uom_uom u ON (u.id=t.uom_id)
                    LEFT JOIN pos_session session ON (session.id = pos.session_id)
                    LEFT JOIN pos_config config ON (config.id = session.config_id)
                left join product_pricelist pp on (pos.pricelist_id = pp.id)
        '''
        return from_

    def _where_pos(self):
        where_ = 'l.sale_order_line_id is NULL'
        return where_

    def _group_by_pos(self):
        groupby_ = '''
            l.order_id,
            l.product_id,
            l.price_unit,
            l.discount,
            l.qty,
            t.uom_id,
            t.categ_id,
            pos.name,
            pos.date_order,
            pos.partner_id,
            pos.user_id,
            pos.state,
            pos.company_id,
            pos.pricelist_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            u.factor,
            pos.crm_team_id
        '''
        return groupby_

    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        if not fields:
            fields = {}
        res = super()._query(with_clause, fields, groupby, from_clause)
        current = '(SELECT %s FROM %s WHERE %s GROUP BY %s)' % \
                  (self._select_pos(fields), self._from_pos(), self._where_pos(), self._group_by_pos())

        return '%s UNION ALL %s' % (res, current)
