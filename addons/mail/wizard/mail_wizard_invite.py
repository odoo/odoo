# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from lxml.html import builder as html
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Invite(models.TransientModel):
    """ Wizard to invite partners (or channels) and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    res_model = fields.Char('Related Document Model', required=True, help='Model of the followed resource')
    res_id = fields.Integer('Related Document ID', help='Id of the followed resource')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    message = fields.Html('Message')
    notify = fields.Boolean('Notify Recipients', default=True)

    def add_followers(self):
        if not self.env.user.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        for wizard in self:
            document = self.env[wizard.res_model].browse(wizard.res_id)
            document.message_subscribe(partner_ids=wizard.partner_ids.ids)
            if wizard.notify:
                model_name = self.env['ir.model']._get(wizard.res_model).display_name
                message_values = wizard._prepare_message_values(document, model_name)
                document.message_notify(**message_values)
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_message_values(self, document, model_name):
        return {
            'body': self.message or "",
            'email_add_signature': False,
            'email_from': self.env.user.email_formatted,
            'email_layout_xmlid': "mail.mail_notification_invite",
            'model': self.res_model,
            'partner_ids': self.partner_ids.ids,
            'record_name': document.display_name,
            'reply_to': self.env.user.email_formatted,
            'reply_to_force_new': True,
            'subject': _('Invitation to follow %(document_model)s: %(document_name)s', document_model=model_name,
                         document_name=document.display_name),
        }
