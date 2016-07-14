# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from odoo import fields as new_fields

class ir_actions_report(osv.Model):
    _inherit = 'ir.actions.report.xml'

    def associated_view(self, cr, uid, ids, context):
        """Used in the ir.actions.report.xml form view in order to search naively after the view(s)
        used in the rendering.
        """
        try:
            report_name = self.browse(cr, uid, ids[0], context).report_name
            act_window_obj = self.pool.get('ir.actions.act_window')
            view_action = act_window_obj.for_xml_id(cr, uid, 'base', 'action_ui_view', context=context)
            view_action['domain'] = [('name', 'ilike', report_name.split('.')[1]), ('type', '=', 'qweb')]
            return view_action
        except:
            return False

    _columns = {'paperformat_id': fields.many2one('report.paperformat', 'Paper format')}

class Actions(osv.Model):
    _inherit = 'ir.actions.report.xml'

    print_report_name = new_fields.Char('Printed Report Name', help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the object and time variables.")
