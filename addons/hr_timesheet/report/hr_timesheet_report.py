
from openerp import tools
from openerp.osv import fields,osv
from openerp.addons.decimal_precision import decimal_precision as dp

class hr_timesheet_report(osv.osv):
    _name = "hr.timesheet.report"
    _description = "Timesheet"
    _auto = False
    _columns = {
        'year': fields.char('Year',size=64,required=False, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'date': fields.date('Date', readonly=True),
        'name': fields.char('Description', size=64,readonly=True),
        'product_id' : fields.many2one('product.product', 'Product',readonly=True),
        'journal_id' : fields.many2one('account.analytic.journal', 'Journal',readonly=True),
        'general_account_id' : fields.many2one('account.account', 'General Account', readonly=True),
        'user_id': fields.many2one('res.users', 'User',readonly=True),
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account',readonly=True),
        'company_id': fields.many2one('res.company', 'Company',readonly=True),
        'cost': fields.float('#Cost',readonly=True, digits_compute=dp.get_precision('Account')),
        'quantity': fields.float('Time',readonly=True),
    }

    def _select(self):
        select_str = """
             SELECT min(hat.id) as id,
                    aal.date as date,
                    to_char(aal.date, 'YYYY-MM-DD') as day,
                    to_char(aal.date,'YYYY') as year,
                    to_char(aal.date,'MM') as month,
                    sum(aal.amount) as cost,
                    sum(aal.unit_amount) as quantity,
                    aal.account_id as account_id,
                    aal.journal_id as journal_id,
                    aal.product_id as product_id,
                    aal.general_account_id as general_account_id,
                    aal.user_id as user_id,
                    aal.company_id as company_id,
                    aal.currency_id as currency_id
        """
        return select_str

    def _from(self):
        from_str = """
                account_analytic_line as aal
                    left join hr_analytic_timesheet as hat ON (hat.line_id=aal.id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY aal.date,
                    aal.account_id,
                    aal.product_id,
                    aal.general_account_id,
                    aal.journal_id,
                    aal.user_id,
                    aal.company_id,
                    aal.currency_id
        """
        return group_by_str

    def init(self, cr):
        # self._table = hr_timesheet_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
