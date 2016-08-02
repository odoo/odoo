# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Vincent Renaville

from odoo import api, fields, models, _


class ReportWebkitActions(models.TransientModel):
    _name = "report.webkit.actions"
    _description = "Webkit Actions"

    print_button = fields.Boolean('Add print button', default=True, help="Check this to add a Print action for this Report in the sidebar of the corresponding document types")
    open_action = fields.Boolean('Open added action', help="Check this to view the newly added internal print action after creating it (technical view) ")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ReportWebkitActions, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        record_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if not record_id or (active_model != 'ir.actions.report.xml'):
            return res

        report = self.env['ir.actions.report.xml'].browse(record_id)
        if self.env['ir.values'].search([('value', '=', report.type + ',' + str(record_id))]):
            res['arch'] = '''<form string="Add Print Buttons">
                                 <label string="Report Action already exist for this report."/>
                             </form> 
                            '''
        return res

    @api.multi
    def do_action(self):
        """ This Function Open added Action.
         @param self: The object pointer.
         @return: Dictionary of ir.values form.
        """
        IrValues = self.env['ir.values']
        active_id = self.env.context.get('active_id', False)
        for current in self:
            report = self.env['ir.actions.report.xml'].browse(active_id)
            if current.print_button:
                res = IrValues.set('action', 'client_print_multi', report.report_name, [report.model],
                                   'ir.actions.report.xml,%d' % active_id, isobject=True)
            else:
                res = IrValues.set('action', 'client_print_multi', report.report_name, [report.model, 0],
                                   'ir.actions.report.xml,%d' % active_id, isobject=True)
            if res[0]:
                if not current.open_action:
                    return {'type': 'ir.actions.act_window_close'}

                return {
                    'name': _('Client Actions Connections'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_id': res[0],
                    'res_model': 'ir.values',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                }
