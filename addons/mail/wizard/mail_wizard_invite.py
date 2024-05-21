# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from lxml.html import builder as html

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup


class Invite(models.TransientModel):
    """ Wizard to invite partners (or channels) and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    res_model = fields.Char('Related Document Model', required=True, help='Model of the followed resource')
    res_id = fields.Integer('Related Document ID', help='Id of the followed resource')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    message = fields.Html('Message')

    def add_followers(self):
        for wizard in self:
            Model = self.env[wizard.res_model]
            document = Model.browse(wizard.res_id)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_partners = wizard.partner_ids - document.sudo().message_partner_ids
            document.message_subscribe(partner_ids=new_partners.ids)
        return {'type': 'ir.actions.act_window_close'}

    def add_followers_notify(self):
        user_from = self.env.user
        if not user_from.email:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        for wizard in self:
            Model = self.env[wizard.res_model]
            document = Model.browse(wizard.res_id)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_partners = wizard.partner_ids - document.sudo().message_partner_ids
            document.message_subscribe(partner_ids=new_partners.ids)

            model_name = self.env['ir.model']._get(wizard.res_model).display_name
            message_values = wizard._prepare_message_values(document, model_name, user_from)
            message_values['partner_ids'] = new_partners.ids
            message_values['subtype_xmlid'] = "mail.mt_comment"
            document.message_notify(**message_values)
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_message_values(self, document, model_name, user_from):
        image_url = f"/web/image/res.partner/{user_from.partner_id.id}/avatar_128"
        body = Markup("%(avatar)s<p>%(name_from)s (%(email_from)s) %(content)s %(message)s</p>") % {
            'avatar': Markup("<img style='height:20px;margin-top:16px;width:20px;margin-right:5px;' alt='Avatar' src=%s/>") % image_url,
            'name_from': user_from.name,
            'email_from': user_from.email,
            'content': _("added you as a follower to this document"),
            'message': self.message
        }

        return {
            'subject': _('Invitation to follow %(document_model)s: %(document_name)s', document_model=model_name,
                         document_name=document.display_name),
            'body': body,
            'record_name': document.display_name,
            'email_from': user_from.email_formatted,
            'reply_to': user_from.email_formatted,
            'model': self.res_model,
            'res_id': self.res_id,
            'reply_to_force_new': True,
            'email_add_signature': False,
        }
