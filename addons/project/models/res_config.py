# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class project_configuration(osv.osv_memory):
    _name = 'project.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_pad': fields.selection([
            (0, "Task description is a plain text"),
            (1, "Collaborative rich text on task description")
            ], "Pads",
            help='Lets the company customize which Pad installation should be used to link to new pads '
                 '(for example: http://ietherpad.com/).\n'
                 '-This installs the module pad.'),
        'module_rating_project': fields.selection([
            (0, "No customer rating"),
            (1, 'Allow activating customer rating on projects, at issue completion')
            ], "Rating",
            help="This allows customers to give rating on provided services"),
        'generate_project_alias': fields.selection([
            (0, "Do not create an email alias automatically"),
            (1, "Automatically generate an email alias at the project creation")
            ], "Project Alias",
            help="Odoo will generate an email alias at the project creation from project name."),
        'module_project_forecast': fields.boolean("Forecasts, planning and Gantt charts"),
    }

    def set_default_generate_project_alias(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).generate_project_alias
        check = self.pool['res.users'].has_group(cr, uid, 'base.group_system')
        self.pool.get('ir.values').set_default(cr, check and SUPERUSER_ID or uid, 'project.config.settings', 'generate_project_alias', config_value)
