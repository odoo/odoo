# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from lxml.html import builder as html

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty


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
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    message = fields.Html('Message')
    notify = fields.Boolean('Send Notification', default=True)

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
            # send a notification if option checked and if a message exists (do not send void notifications)
            if wizard.notify and wizard.message and not is_html_empty(wizard.message):
                message_values = wizard._prepare_message_values(document, model_name, email_from)
                message_values['partner_ids'] = new_partners.ids
                document.message_notify(**message_values)
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
