# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp import tools


class Invite(models.TransientModel):
    """ Wizard to invite partners and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    @api.model
    def default_get(self, fields):
        result = super(Invite, self).default_get(fields)
        user_name = self.env.user.name_get()[0][1]
        model = result.get('res_model')
        res_id = result.get('res_id')
        if 'message' in fields and model and res_id:
            model_name = self.env['ir.model'].search([('model', '=', self.pool[model]._name)]).name_get()[0][1]
            document_name = self.env[model].browse(res_id).name_get()[0][1]
            message = _('<div><p>Hello,</p><p>%s invited you to follow %s document: %s.<p></div>') % (user_name, model_name, document_name)
            result['message'] = message
        elif 'message' in fields:
            result['message'] = _('<div><p>Hello,</p><p>%s invited you to follow a new document.</p></div>') % user_name
        return result

    res_model = fields.Char('Related Document Model', required=True, select=1, help='Model of the followed resource')
    res_id = fields.Integer('Related Document ID', select=1, help='Id of the followed resource')
    partner_ids = fields.Many2many('res.partner', string='Recipients', help="List of partners that will be added as follower of the current document.")
    channel_ids = fields.Many2many('mail.channel', string='Channels', help='List of channels that will be added as listeners of the current document.')
    message = fields.Html('Message')
    send_mail = fields.Boolean('Send Email', default=True, help="If checked, the partners will receive an email warning they have been added in the document's followers.")

    @api.multi
    def add_followers(self):
        email_from = self.env['mail.message']._get_default_from()
        for wizard in self:
            Model = self.env[wizard.res_model]
            document = Model.browse(wizard.res_id)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_partners = wizard.partner_ids - document.message_partner_ids
            new_channels = wizard.channel_ids - document.message_channel_ids
            document.message_subscribe(new_partners.ids, new_channels.ids)

            model_ids = self.env['ir.model'].search([('model', '=', wizard.res_model)])
            model_name = model_ids.name_get()[0][1]
            print "@@@@@", wizard.message
            # send an email if option checked and if a message exists (do not send void emails)
            if wizard.send_mail and wizard.message and not wizard.message == '<br>':  # when deleting the message, cleditor keeps a <br>
                # TDE FIXME: use a template + _notification methods
                # add signature
                signature = self.env.user.signature
                wizard.message = tools.append_content_to_html(wizard.message, signature, plaintext=False, container_tag='div')

                # send mail to new followers
                self.env['mail.mail'].create({
                    'model': wizard.res_model,
                    'res_id': wizard.res_id,
                    'record_name': document.name_get()[0][1],
                    'email_from': email_from,
                    'reply_to': email_from,
                    'subject': _('Invitation to follow %s: %s') % (model_name, document.name_get()[0][1]),
                    'body_html': '%s' % wizard.message,
                    'auto_delete': True,
                    'message_id': self.env['mail.message']._get_message_id({'no_auto_thread': True}),
                    'recipient_ids': [(4, id) for id in new_partners.ids]}).send()
        return {'type': 'ir.actions.act_window_close'}
