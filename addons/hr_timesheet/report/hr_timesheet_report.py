
from openerp import tools, models, fields
from openerp.addons.decimal_precision import decimal_precision as dp


class hr_timesheet_report(models.Model):
    _name = "hr.timesheet.report"
    _description = "Timesheet"
    _auto = False
    _rec_name = "date"

    date = fields.Date('Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    cost = fields.Float('Cost', readonly=True, digits=dp.get_precision('Account'))
    quantity = fields.Float('Time', readonly=True)

    def _select(self):
        select_str = """
             SELECT min(aal.id) as id,
                    aal.date as date,
                    sum(aal.amount) as cost,
                    sum(aal.unit_amount) as quantity,
                    aal.account_id as account_id,
                    aal.product_id as product_id,
                    aal.user_id as user_id,
                    aal.company_id as company_id,
                    aal.currency_id as currency_id
        """
        return select_str

    def _from(self):
        from_str = """
            FROM account_analytic_line as aal
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY aal.date,
                    aal.account_id,
                    aal.product_id,
                    aal.user_id,
                    aal.company_id,
                    aal.currency_id
        """
        return group_by_str

    def _where(self):
        where_str = """
            WHERE aal.is_timesheet IS TRUE
        """
        return where_str

    def init(self, cr):
        # self._table = hr_timesheet_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
            %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))
