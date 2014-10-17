# -*- coding: utf-8 -*-
from openerp import models, fields, tools


class report_lunch_order(models.Model):
    _name = "report.lunch.order.line"
    _description = "Lunch Orders Statistics"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date('Date Order', readonly=True, select=True)
    year = fields.Char('Year', size=4, readonly=True)
    month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True)
    day = fields.Char('Day', size=128, readonly=True)
    user_id = fields.Many2one('res.users', 'User Name')
    price_total = fields.Float('Total Price', readonly=True)
    note = fields.Text('Note', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_lunch_order_line')
        cr.execute("""
            create or replace view report_lunch_order_line as (
               select
                   min(lo.id) as id,
                   lo.user_id as user_id,
                   lo.date as date,
                   to_char(lo.date, 'YYYY') as year,
                   to_char(lo.date, 'MM') as month,
                   to_char(lo.date, 'YYYY-MM-DD') as day,
                   lo.note as note,
                   sum(lp.price) as price_total

            from
                   lunch_order_line as lo
                   left join lunch_product as lp on (lo.product_id = lp.id)
            group by
                   lo.date,lo.user_id,lo.note
            )
            """)
