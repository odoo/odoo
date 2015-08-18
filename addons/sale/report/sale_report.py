# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import fields, osv

class sale_report(osv.osv):
    _name = "sale.report"
    _description = "Sales Orders Statistics"
    _auto = False
    _rec_name = 'date'

    _columns = {
        'date': fields.datetime('Date Order', readonly=True),  # TDE FIXME master: rename into date_order
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'product_uom_qty': fields.float('# of Qty', readonly=True),

        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'currency_price_total': fields.float('Amount in Currency', readonly=True),
        'delay': fields.float('Commitment Delay', digits=(16,2), readonly=True),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', readonly=True),
        'categ_id': fields.many2one('product.category','Product Category', readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'state': fields.selection([
            ('cancel', 'Cancelled'),
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('exception', 'Exception'),
            ('done', 'Done')], 'Order Status', readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'invoiced': fields.boolean('Paid', readonly=True),
        'nbr_paid': fields.integer('# of Paid Lines', readonly=True),
        'team_id': fields.many2one('crm.team', 'Sales Team', readonly=True, oldname='section_id'),
        'country_id': fields.many2one('res.country', 'Partner Country', readonly=True),
        'commercial_partner_id': fields.many2one('res.partner', 'Commercial Entity', readonly=True),
        'currency_rate':fields.float('Currency Rate',readonly=True),
    }
    _order = 'date desc'

    def _select(self):
        select_str = """
            WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                    SELECT r.currency_id, r.rate, r.name AS date_start,
                        (SELECT name FROM res_currency_rate r2
                        WHERE r2.name > r.name AND
                            r2.currency_id = r.currency_id
                         ORDER BY r2.name ASC
                         LIMIT 1) AS date_end
                    FROM res_currency_rate r
                )
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(((l.price_unit*l.product_uom_qty)* (100.0 - l.discount)) / 100.0) as currency_price_total,
                    sum((((l.price_unit*l.product_uom_qty)*(ccr.rate/cr.rate))* (100.0 - l.discount)) / 100.0) as price_total,
                    count(*) as nbr,
                    s.date_order as date,
                    s.date_confirm as date_confirm,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    l.state,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id,
                    s.team_id as team_id,
                    p.product_tmpl_id,
                    l.invoiced::integer as nbr_paid,
                    l.invoiced,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    coalesce(cr.rate,1) as currency_rate
        """
        return select_str

    def _from(self):
        from_str = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                    join currency_rate cr on (cr.currency_id = pp.currency_id and
                        cr.date_start <= s.date_order and
                        (cr.date_end is null or cr.date_end > s.date_order))
                    join res_company rc on rc.id=s.company_id
                        left join currency_rate ccr on(ccr.currency_id=rc.currency_id and ccr.date_start <= s.date_order and (ccr.date_end is null or ccr.date_end > s.date_order))
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    l.state,
                    s.pricelist_id,
                    s.project_id,
                    s.team_id,
                    p.product_tmpl_id,
                    l.invoiced,
                    partner.country_id,
                    partner.commercial_partner_id,
                    cr.rate,
                    ccr.rate
        """
        return group_by_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))
