# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class CrmPhoneCall2PhoneCall(models.TransientModel):
    _name = 'crm.phonecall2phonecall'
    _description = 'Phonecall To Phonecall'

    @api.model
    def default_get(self, fields_list):
        """
        This function gets default values
        """
        res = super(CrmPhoneCall2PhoneCall, self).default_get(fields_list)
        phonecall_id = self.env.context.get('active_id')
        res.update({'action': 'schedule', 'date': fields.Datetime.now()})
        if phonecall_id:
            phonecall = self.env['crm.phonecall'].browse(phonecall_id)

            categ_id = False
            try:
                categ_id = self.env.ref('crm.categ_phone2').id
            except ValueError:
                pass

            if 'name' in fields_list:
                res['name'] = phonecall.name
            if 'user_id' in fields_list:
                res['user_id'] = phonecall.user_id.id
            if 'date' in fields_list:
                res['date'] = False
            if 'team_id' in fields_list:
                res['team_id'] = phonecall.team_id.id
            if 'categ_id' in fields_list:
                res['categ_id'] = categ_id
            if 'partner_id' in fields_list:
                res['partner_id'] = phonecall.partner_id.id
        return res

    name = fields.Char(string='Call summary', required=True, index=True)
    user_id = fields.Many2one('res.users', string="Assign To")
    contact_name = fields.Char(string='Contact')
    phone = fields.Char()
    categ_id = fields.Many2one('crm.phonecall.category', string='Category')
    date = fields.Datetime()
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id')
    action = fields.Selection([('schedule', 'Schedule a call'), ('log', 'Log a call')], required=True)
    partner_id = fields.Many2one('res.partner', string="Partner")
    note = fields.Text()

    def action_cancel(self):
        """
        Closes Phonecall to Phonecall form
        """
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_schedule(self):
        phonecall = self.env['crm.phonecall'].browse(
            self.env.context.get('active_id'))
        for this in self:
            phonecall_ids = phonecall.schedule_another_phonecall(
                this.date, this.name,
                this.user_id.id,
                this.team_id.id,
                this.categ_id.id,
                action=this.action)
        return phonecall_ids[phonecall.id].redirect_phonecall_view()
