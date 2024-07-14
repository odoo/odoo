# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp_message', 'WhatsApp')],
        ondelete={'whatsapp_message': lambda recs: recs.write({'message_type': 'comment'})},
    )
    wa_message_ids = fields.One2many('whatsapp.message', 'mail_message_id', string='Related WhatsApp Messages')

    def _post_whatsapp_reaction(self, reaction_content, partner_id):
        self.ensure_one()
        reaction_to_delete = self.reaction_ids.filtered(lambda r: r.partner_id == partner_id)
        reactionGroups = []
        if reaction_to_delete:
            content = reaction_to_delete.content
            reaction_to_delete.unlink()
            reactionGroups.append(self._get_whatsapp_reaction_format(content, partner_id, unlink_reaction=True))
        if reaction_content and self.id:
            self.env['mail.message.reaction'].create({
                'message_id': self.id,
                'content': reaction_content,
                'partner_id': partner_id.id,
            })
            reactionGroups.append(self._get_whatsapp_reaction_format(reaction_content, partner_id))
        payload = {'Message': {'id': self.id, 'reactions': reactionGroups}}
        self.env['bus.bus']._sendone(self._bus_notification_target(), 'mail.record/insert', payload)

    def _get_whatsapp_reaction_format(self, content, partner_id, unlink_reaction=False):
        self.ensure_one()
        group_domain = [('message_id', '=', self.id), ('content', '=', content)]
        count = self.env['mail.message.reaction'].search_count(group_domain)
        # remove old reaction and add new one if count > 0 from same partner
        group_command = 'ADD' if count > 0 else 'DELETE'
        return (group_command, {
            'content': content,
            'count': count,
            'guests': [],
            'message': {'id': self.id},
            'partners': [('DELETE' if unlink_reaction else 'ADD', {'id': partner_id.id})],
        })

    def message_format(self, *args, **kwargs):
        vals_list = super().message_format(*args, **kwargs)
        whatsapp_mail_message = self.filtered(lambda m: m.message_type == 'whatsapp_message')
        if whatsapp_mail_message:
            whatsapp_message_by_message_id = {
                whatsapp_message.mail_message_id.id: whatsapp_message
                for whatsapp_message in self.env['whatsapp.message'].sudo().search([('mail_message_id', 'in', whatsapp_mail_message.ids)])
            }
            for vals in vals_list:
                if whatsapp_message_by_message_id.get(vals['id']):
                    vals['whatsappStatus'] = whatsapp_message_by_message_id[vals['id']].state
        return vals_list
