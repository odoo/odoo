# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from lxml.html import builder as html

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
from odoo.addons.mail.tools.parser import parse_res_ids


class MailFollowersEdit(models.TransientModel):
    """ Wizard to edit partners (or channels) and make them followers. """
    _name = 'mail.followers.edit'
    _description = 'Mail Followers Edit'

    @api.model
    def default_get(self, fields):
        result = super(MailFollowersEdit, self).default_get(fields)
        if 'message' not in fields:
            return result

        user_name = self.env.user.display_name
        model = result.get('res_model')
        res_ids = parse_res_ids(result.get('res_ids'))
        if model and res_ids:
            document = self.env['ir.model']._get(model).display_name
            titles = [self.env[model].browse(res_id).display_name for res_id in res_ids]
            if len(titles) == 1:
                title = titles[0]
                msg_fmt = _('%(user_name)s invited you to follow %(document)s document: %(title)s')
            else:
                title = ', '.join(titles)
                msg_fmt = _('%(user_name)s invited you to follow %(document)s documents: %(title)s')
        else:
            msg_fmt = _('%(user_name)s invited you to follow a new document.')

        text = msg_fmt % locals()
        message = html.DIV(
            html.P(_('Hello,')),
            html.P(text)
        )
        result['message'] = etree.tostring(message)
        return result

    operation = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove'),
    ], string='Operation', required=True, default='add')
    res_model = fields.Char('Related Document Model', required=True, help='Model of the followed resource')
    res_ids = fields.Char('Related Document IDs', help='Ids of the followed resources')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    message = fields.Html('Message')
    notify = fields.Boolean('Send Notification', compute='_compute_notify', readonly=False)

    @api.depends('operation')
    def _compute_notify(self):
        for wizard in self:
            wizard.notify = wizard.operation == 'add'

    def edit_followers(self):
        for wizard in self:
            Model = self.env[wizard.res_model]
            res_ids = parse_res_ids(wizard.res_ids)
            documents = Model.browse(res_ids)
            if wizard.operation == 'remove':
                for document in documents:
                    document.message_unsubscribe(partner_ids=wizard.partner_ids.ids)
            else:
                if not self.env.user.email:
                    raise UserError(_("Unable to post message, please configure the sender's email address."))
                email_from = self.env.user.email_formatted
                for document in documents:
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
            'res_id': document.id,
            'reply_to_force_new': True,
            'email_add_signature': True,
        }
