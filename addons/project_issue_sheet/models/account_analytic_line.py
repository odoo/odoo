#-*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'account analytic line'
    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }
