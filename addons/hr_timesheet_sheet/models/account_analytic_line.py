# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
 from openerp.tools.translate import _
 from openerp.exceptions import UserError


class account_analytic_line(osv.osv):
    _inherit = "account.analytic.line"

    def _get_default_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        # get the default date (should be: today)
        res = super(account_analytic_line, self)._get_default_date(cr, uid, context=context)
        # if we got the dates from and to from the timesheet and if the default date is in between, we use the default
        # but if the default isn't included in those dates, we use the date start of the timesheet as default
        if context.get('timesheet_date_from') and context.get('timesheet_date_to'):
            if context['timesheet_date_from'] <= res <= context['timesheet_date_to']:
                return res
            return context.get('timesheet_date_from')
        # if we don't get the dates from the timesheet, we return the default value from super()
        return res

    def _sheet(self, cursor, user, ids, name, args, context=None):
        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
        res = {}.fromkeys(ids, False)
        for ts_line in self.browse(cursor, user, ids, context=context):
            if not ts_line.project_id:
                continue
            sheet_ids = sheet_obj.search(cursor, user,
                [('date_to', '>=', ts_line.date), ('date_from', '<=', ts_line.date),
                 ('employee_id.user_id', '=', ts_line.user_id.id),
                 ('state', 'in', ['draft', 'new'])],
                context=context)
            if sheet_ids:
            # [0] because only one sheet possible for an employee between 2 dates
                res[ts_line.id] = sheet_obj.name_get(cursor, user, sheet_ids, context=context)[0]
        return res

    def _get_hr_timesheet_sheet(self, cr, uid, ids, context=None):
        ts_line_ids = []
        for ts in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                    SELECT l.id
                        FROM account_analytic_line l
                    WHERE %(date_to)s >= l.date
                        AND %(date_from)s <= l.date
                        AND %(user_id)s = l.user_id
                        AND l.project_id IS NOT NULL
                    GROUP BY l.id""", {'date_from': ts.date_from,
                                        'date_to': ts.date_to,
                                        'user_id': ts.employee_id.user_id.id,})
            ts_line_ids.extend([row[0] for row in cr.fetchall()])
        return ts_line_ids

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet', select="1",
            type='many2one', relation='hr_timesheet_sheet.sheet', ondelete="cascade",
            store={
                    'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet, ['employee_id', 'date_from', 'date_to'], 10),
                    'account.analytic.line': (lambda self,cr,uid,ids,context=None: ids, ['user_id', 'date'], 10),
                  },
            ),
    }

    def write(self, cr, uid, ids, values, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(account_analytic_line, self).write(cr, uid, ids, values,context=context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(account_analytic_line,self).unlink(cr, uid, ids,*args, **kwargs)

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise UserError(_('You cannot modify an entry in a confirmed timesheet.'))
        return True
