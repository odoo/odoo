# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api


class PosDetails(models.TransientModel):
    _name = 'pos.details'
    _description = 'Sales Details'

    date_start = fields.Date(string='Date Start', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='Date End', required=True, default=fields.Date.context_today)
    user_ids = fields.Many2many('res.users', 'pos_details_report_user_rel', 'user_id', 'wizard_id', string='Salespeople')

    @api.multi
    def print_report(self):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : retrun report
        """
        self.ensure_one()
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read(['date_start', 'date_end', 'user_ids'])
        res = res and res[0] or {}
        datas['form'] = res
        if res.get('id', False):
            datas['ids'] = [res['id']]
        return self.env['report'].get_action(self, 'point_of_sale.report_detailsofsales', data=datas)
