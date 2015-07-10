# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_employee(osv.Model):
    _inherit = "hr.employee"

    def _newly_hired_employee(self, cr, uid, ids, field_name, arg, context=None):
        data = self.pool['hr.applicant'].read_group(cr, uid,
            [('emp_id', 'in', ids), ('job_id.state', '=', 'recruit')],
            ['emp_id'], ['emp_id'], context=context)
        result = dict.fromkeys(ids, False)
        for d in data:
            if d['emp_id_count'] >= 1:
                result[d['emp_id'][0]] = True
        return result

    def _search_newly_hired_employee(self, cr, uid, obj, name, args, context=None):
        applicant_ids = self.pool['hr.applicant'].search_read(cr, uid, [('job_id.state', '=', 'recruit')], ['emp_id'], context=context)
        hired_emp_ids = [applicant['emp_id'][0] for applicant in applicant_ids if applicant['emp_id']]
        return [('id', 'in', hired_emp_ids)]

    _columns = {
        'newly_hired_employee': fields.function(_newly_hired_employee, fnct_search=_search_newly_hired_employee, type='boolean', string='Newly hired employees')
    }
