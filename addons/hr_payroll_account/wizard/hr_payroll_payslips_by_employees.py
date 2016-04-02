# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

class hr_payslip_employees(osv.osv_memory):

    _inherit ='hr.payslip.employees'
    
    def compute_sheet(self, cr, uid, ids, context=None):
        run_pool = self.pool.get('hr.payslip.run')
        if context is None:
            context = {}
        if context.get('active_id'):
            run_data = run_pool.read(cr, uid, context['active_id'], ['journal_id'])
        journal_id = run_data.get('journal_id')
        journal_id = journal_id and journal_id[0] or False
        if journal_id:
            context = dict(context, journal_id=journal_id)
        return super(hr_payslip_employees, self).compute_sheet(cr, uid, ids, context=context)
