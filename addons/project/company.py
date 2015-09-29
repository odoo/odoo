# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'project_time_mode_id': fields.many2one('product.uom', 'Project Time Unit',
            help='This will set the unit of measure used in projects and tasks.\n' \
"If you use the timesheet linked to projects (project_timesheet module), don't " \
"forget to setup the right unit of measure in your employees.",
        ),
    }
