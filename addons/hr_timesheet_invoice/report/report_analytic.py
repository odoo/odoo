# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv
from openerp import tools
from openerp.addons.decimal_precision import decimal_precision as dp


class report_analytic_account_close(osv.osv):
    _name = "report.analytic.account.close"
    _description = "Analytic account to close"
    _auto = False
    _columns = {
        'name': fields.many2one('account.analytic.account', 'Analytic account', readonly=True),
        'state': fields.char('Status', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'quantity': fields.float('Quantity', readonly=True),
        'quantity_max': fields.float('Max. Quantity', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'date_deadline': fields.date('Deadline', readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_analytic_account_close')
        cr.execute("""
            create or replace view report_analytic_account_close as (
                select
                    a.id as id,
                    a.id as name,
                    a.state as state,
                    sum(l.unit_amount) as quantity,
                    sum(l.amount) as balance,
                    a.partner_id as partner_id,
                    a.quantity_max as quantity_max,
                    a.date as date_deadline
                from
                    account_analytic_line l
                right join
                    account_analytic_account a on (l.account_id=a.id)
                group by
                    a.id,a.state, a.quantity_max,a.date,a.partner_id
                having
                    (a.quantity_max>0 and (sum(l.unit_amount)>=a.quantity_max)) or
                    a.date <= current_date
            )""")

class report_account_analytic_line_to_invoice(osv.osv):
    _name = "report.account.analytic.line.to.invoice"
    _description = "Analytic lines to invoice report"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic account', readonly=True),
        'product_uom_id':fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'unit_amount': fields.float('Units', readonly=True),
        'sale_price': fields.float('Sale price', readonly=True, digits_compute=dp.get_precision('Product Price')),
        'amount': fields.float('Amount', readonly=True, digits=0),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
    }
    _order = 'name desc, product_id asc, account_id asc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_analytic_line_to_invoice')
        cr.execute("""
            CREATE OR REPLACE VIEW report_account_analytic_line_to_invoice AS (
                SELECT
                    DISTINCT(to_char(l.date,'MM')) as month,
                    to_char(l.date, 'YYYY') as name,
                    MIN(l.id) AS id,
                    l.product_id,
                    l.account_id,
                    SUM(l.amount) AS amount,
                    SUM(l.unit_amount*t.list_price) AS sale_price,
                    SUM(l.unit_amount) AS unit_amount,
                    l.product_uom_id
                FROM
                    account_analytic_line l
                left join
                    product_product p on (l.product_id=p.id)
                left join
                    product_template t on (p.product_tmpl_id=t.id)
                WHERE
                    (invoice_id IS NULL) and (to_invoice IS NOT NULL)
                GROUP BY
                    to_char(l.date, 'YYYY'), to_char(l.date,'MM'), product_id, product_uom_id, account_id
            )
        """)
