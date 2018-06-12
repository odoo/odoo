
from odoo import fields, models


class Channel(models.Model):
    _inherit = 'mail.channel'

    public = fields.Selection(selection_add=[('department', 'Selected department')])
    department_id = fields.Many2one('hr.department', 'Department')

    def _subscribe_users(self):
        super(Channel, self)._subscribe_users()
        for mail_channel in self:
            if mail_channel.public == 'department':
                # Remove partners that are not in selected department
                mail_channel.write(
                    {'channel_partner_ids':
                        [(3, pid) for pid in [pid for pid in mail_channel.channel_partner_ids.ids if pid not in mail_channel.department_id.mapped('member_ids').mapped('user_id').mapped('partner_id').ids]]})
                # Add partners that are in selected department
                mail_channel.write(
                    {'channel_partner_ids':
                        [(4, pid) for pid in mail_channel.department_id.mapped('member_ids').mapped('user_id').mapped('partner_id').ids]})

    def write(self, vals):
        res = super(Channel, self).write(vals)
        if vals.get('department_id'):
            self._subscribe_users()
        return res

    def channel_fetch_slot(self):
        values = super(Channel, self).channel_fetch_slot()
        my_partner_id = self.env.user.partner_id.id
        depChannels = self.search([('channel_type', '=', 'channel'), ('public', '=', 'department'), ('channel_partner_ids', 'in', [my_partner_id])]).channel_info()
        values['channel_private_group'].extend(depChannels)
        return values
