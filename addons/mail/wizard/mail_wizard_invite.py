# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from lxml.html import builder as html

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Invite(models.TransientModel):
    """ Wizard to invite partners (or channels) and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    @api.model
    def default_get(self, fields):
        result = super(Invite, self).default_get(fields)
        if 'message' not in fields:
            return result

        user_name = self.env.user.display_name
        model = result.get('res_model')
        res_id = result.get('res_id')
        if model and res_id:
            document = self.env['ir.model']._get(model).display_name
            title = self.env[model].browse(res_id).display_name
            msg_fmt = _('%(user_name)s invited you to follow %(document)s document: %(title)s')
        else:
            msg_fmt = _('%(user_name)s invited you to follow a new document.')

        text = msg_fmt % locals()
        message = html.DIV(
            html.P(_('Hello,')),
            html.P(text)
        )
        result['message'] = etree.tostring(message)
        return result

    res_model = fields.Char('Related Document Model', required=True, help='Model of the followed resource')
    res_id = fields.Integer('Related Document ID', help='Id of the followed resource')
    partner_ids = fields.Many2many('res.partner', string='Recipients', help="List of partners that will be added as follower of the current document.",
                                   domain=[('type', '!=', 'private')])
    message = fields.Html('Message')
    send_mail = fields.Boolean('Send Email', default=True, help="If checked, the partners will receive an email warning they have been added in the document's followers.")

    def add_followers(self):
        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        email_from = self.env.user.email_formatted
        for wizard in self:
            Model = self.env[wizard.res_model]
            document = Model.browse(wizard.res_id)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_partners = wizard.partner_ids - document.sudo().message_partner_ids
            document.message_subscribe(partner_ids=new_partners.ids)

            model_name = self.env['ir.model']._get(wizard.res_model).display_name
            # send an email if option checked and if a message exists (do not send void emails)
            if wizard.send_mail and wizard.message and not wizard.message == '<br>':  # when deleting the message, cleditor keeps a <br>
                message = self.env['mail.message'].create(
                    self._prepare_message_values(document, model_name, email_from)
                )
                email_partners_data = []
                recipients_data = self.env['mail.followers']._get_recipient_data(document, 'comment', False, pids=new_partners.ids)[document.id]
                for _pid, pdata in recipients_data.items():
                    pdata['notif'] = 'email'
                    email_partners_data.append(pdata)

                document._notify_thread_by_email(
                    message, email_partners_data,
                    send_after_commit=False
                )
                # in case of failure, the web client must know the message was
                # deleted to discard the related failure notification
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'mail.message/delete', {'message_ids': message.ids})
                message.unlink()
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_message_values(self, document, model_name, email_from):
        return {
            'subject': _('Invitation to follow %(document_model)s: %(document_name)s', document_model=model_name,
                         document_name=document.display_name),
            'body': self.message,
            'record_name': document.display_name,
            'email_from': email_from,
            'reply_to': email_from,
            'model': self.res_model,
            'res_id': self.res_id,
            'reply_to_force_new': True,
            'email_add_signature': True,
        }
