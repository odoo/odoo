# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from openerp.osv import fields,osv
from openerp import tools

class purchase_report(osv.osv):
    _name = "purchase.report"
    _description = "Purchases Orders"
    _auto = False
    _columns = {
        'date': fields.datetime('Order Date', readonly=True, help="Date on which this document has been created"),  # TDE FIXME master: rename into date_order
        'state': fields.selection([('draft', 'Draft RFQ'),
                                   ('sent', 'RFQ Sent'),
                                   ('to approve', 'To Approve'),
                                   ('purchase', 'Purchase Order'),
                                   ('done', 'Done'),
                                   ('cancel', 'Cancelled')
                                  ],'Order Status', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'picking_type_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Vendor', readonly=True),
        'date_approve':fields.date('Date Approved', readonly=True),
        'product_uom' : fields.many2one('product.uom', 'Reference Unit of Measure', required=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'delay':fields.float('Days to Validate', digits=(16,2), readonly=True),
        'delay_pass':fields.float('Days to Deliver', digits=(16,2), readonly=True),
        'quantity': fields.float('Product Quantity', readonly=True),  # TDE FIXME master: rename into unit_quantity
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True, group_operator="avg"),
        'negociation': fields.float('Purchase-Standard Price', readonly=True, group_operator="avg"),
        'price_standard': fields.float('Products Value', readonly=True, group_operator="sum"),
        'nbr': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'category_id': fields.many2one('product.category', 'Product Category', readonly=True),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', readonly=True),
        'country_id': fields.many2one('res.country', 'Partner Country', readonly=True),
        'fiscal_position_id': fields.many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position', readonly=True),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'commercial_partner_id': fields.many2one('res.partner', 'Commercial Entity', readonly=True),
    }
    _order = 'date desc, price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'purchase_report')
        cr.execute("""
            create or replace view purchase_report as (
                WITH currency_rate as (%s)
                select
                    min(l.id) as id,
                    s.date_order as date,
                    s.state,
                    s.date_approve,
                    s.dest_address_id,
                    spt.warehouse_id as picking_type_id,
                    s.partner_id as partner_id,
                    s.create_uid as user_id,
                    s.company_id as company_id,
                    s.fiscal_position_id as fiscal_position_id,
                    l.product_id,
                    p.product_tmpl_id,
                    t.categ_id as category_id,
                    s.currency_id,
                    t.uom_id as product_uom,
                    sum(l.product_qty/u.factor*u2.factor) as quantity,
                    extract(epoch from age(s.date_approve,s.date_order))/(24*60*60)::decimal(16,2) as delay,
                    extract(epoch from age(l.date_planned,s.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
                    count(*) as nbr,
                    sum(l.price_unit / COALESCE(cr.rate, 1.0) * l.product_qty)::decimal(16,2) as price_total,
                    avg(100.0 * (l.price_unit / COALESCE(cr.rate,1.0) * l.product_qty) / NULLIF(ip.value_float*l.product_qty/u.factor*u2.factor, 0.0))::decimal(16,2) as negociation,
                    sum(ip.value_float*l.product_qty/u.factor*u2.factor)::decimal(16,2) as price_standard,
                    (sum(l.product_qty * l.price_unit / COALESCE(cr.rate, 1.0))/NULLIF(sum(l.product_qty/u.factor*u2.factor),0.0))::decimal(16,2) as price_average,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    analytic_account.id as account_analytic_id
                from purchase_order_line l
                    join purchase_order s on (l.order_id=s.id)
                    join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                            LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id=CONCAT('product.product,',p.id) AND ip.company_id=s.company_id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join stock_picking_type spt on (spt.id=s.picking_type_id)
                    left join account_analytic_account analytic_account on (l.account_analytic_id = analytic_account.id)
                    left join currency_rate cr on (cr.currency_id = s.currency_id and
                        cr.company_id = s.company_id and
                        cr.date_start <= coalesce(s.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
                group by
                    s.company_id,
                    s.create_uid,
                    s.partner_id,
                    u.factor,
                    s.currency_id,
                    l.price_unit,
                    s.date_approve,
                    l.date_planned,
                    l.product_uom,
                    s.dest_address_id,
                    s.fiscal_position_id,
                    l.product_id,
                    p.product_tmpl_id,
                    t.categ_id,
                    s.date_order,
                    s.state,
                    spt.warehouse_id,
                    u.uom_type,
                    u.category_id,
                    t.uom_id,
                    u.id,
                    u2.factor,
                    partner.country_id,
                    partner.commercial_partner_id,
                    analytic_account.id
            )
        """ % self.pool['res.currency']._select_companies_rates())
