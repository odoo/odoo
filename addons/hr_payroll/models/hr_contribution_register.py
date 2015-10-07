#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_contribution_register(osv.osv):
    '''
    Contribution Register
    '''

    _name = 'hr.contribution.register'
    _description = 'Contribution Register'

    _columns = {
        'company_id':fields.many2one('res.company', 'Company'),
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'name':fields.char('Name', required=True, readonly=False),
        'register_line_ids':fields.one2many('hr.payslip.line', 'register_id', 'Register Line', readonly=True),
        'note': fields.text('Description'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
