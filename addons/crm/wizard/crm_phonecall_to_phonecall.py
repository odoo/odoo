# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api, fields, _
import time

class crm_phonecall2phonecall(models.TransientModel):
    _name = 'crm.phonecall2phonecall'
    _description = 'Phonecall To Phonecall'

    name = fields.Char('Call summary', required=True, select=1)
    user_id = fields.Many2one('res.users',"Assign To")
    contact_name = fields.Char('Contact')
    phone = fields.Char('Phone')
    categ_id = fields.Many2one('crm.phonecall.category', 'Category')
    date = fields.Datetime('Date')
    team_id = fields.Many2one('crm.team','Sales Team')
    action = fields.Selection([('schedule','Schedule a call'), ('log','Log a call')], 'Action', required=True)
    partner_id = fields.Many2one('res.partner', "Partner")
    note = fields.Text('Note')

    @api.one
    def action_cancel(self):
        """
        Closes Phonecall to Phonecall form
        """
        return {'type':'ir.actions.act_window_close'}

    @api.multi
    def action_schedule(self):
        value = {}
        phonecall = self.env['crm.phonecall']
        phonecall_ids = self._context.get('active_ids',[])
        for this in self:
            phocall_ids = phonecall.schedule_another_phonecall(phonecall_ids, this.date, this.name, \
                    this.user_id and this.user_id.id or False, \
                    this.team_id and this.team_id.id or False, \
                    this.categ_id and this.categ_id.id or False, \
                    action=this.action)
        return phonecall.redirect_phonecall_view(phocall_ids[phonecall_ids[0]])
    
    @api.model
    def default_get(self, fields):
        """
        This function gets default values
        """
        res = super(crm_phonecall2phonecall, self).default_get(fields)
        record_id = self._context.get('active_id', False)
        res.update({'action': 'schedule', 'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        if record_id:
            phonecall = self.env['crm.phonecall'].browse(record_id)
            categ_id = False
            data_obj = self.pool['ir.model.data']
            try:
                res_id = data_obj._get_id(self._cr, self._uid, 'crm', 'categ_phone2')
                categ_id = data_obj.browse(self._cr, self._uid, res_id, context=self._context).res_id
            except ValueError:
                pass

            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'user_id' in fields:
                res.update({'user_id': phonecall.user_id and phonecall.user_id.id or False})
            if 'date' in fields:
                res.update({'date': False})
            if 'team_id' in fields:
                res.update({'team_id': phonecall.team_id and phonecall.team_id.id or False})
            if 'categ_id' in fields:
                res.update({'categ_id': categ_id})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: