# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def portal_message_format(self, options=None):
        """ Simpler and portal-oriented version of 'message_format'.

        :param dict options: options, used notably for inheritance and adding
          specific fields or properties to compute;

        :return list: list of dict, one per message in self
        """
        self.check_access_rule('read')
        return self._portal_message_format(
            self._portal_get_default_format_properties_names(options=options)
        )

    def _portal_get_default_format_properties_names(self, options=None):
        return {
            'attachment_ids',
            'author_avatar_url',
            'author_id',
            'body',
            'date',
            'id',
            'is_internal',
            'is_message_subtype_note',
            'published_date_str',
            'subtype_id',
        }

    def _portal_message_format(self, properties_names):
        """ Format messages for portal frontend.

        When asking for attachments: ensure an access token is present then
        access them (using sudo).

        :param set properties_names: set of fields / properties to compute

        :return list: list of dict, one per message in self
        """
        message_to_attachments = {}
        if 'attachment_ids' in properties_names:
            properties_names.remove('attachment_ids')
            self.sudo().attachment_ids.generate_access_token()
            related_attachments = {
                att_read_values['id']: att_read_values
                for att_read_values in self.env['ir.attachment'].sudo().browse(
                    self.sudo().attachment_ids.ids
                ).read(
                    ["access_token", "checksum", "id", "mimetype", "name", "res_id", "res_model"]
                )
            }
            message_to_attachments = {
                message.id: [
                    self._portal_message_format_attachments(related_attachments[att_id])
                    for att_id in message.attachment_ids.ids
                ]
                for message in self.sudo()
            }


        fnames = {
            property_name for property_name in properties_names
            if property_name in self._fields and property_name != 'id'
        }
        if fnames:
            vals_list = self._read_format(fnames)
        else:
            vals_list = [{'id': message.id} for message in self]

        note_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        for message, values in zip(self, vals_list):
            if message_to_attachments:
                values['attachment_ids'] = message_to_attachments.get(message.id, {})
            if 'author_avatar_url' in properties_names:
                values['author_avatar_url'] = f'/web/image/mail.message/{message.id}/author_avatar/50x50'
            if 'is_message_subtype_note' in properties_names:
                values['is_message_subtype_note'] = (values.get('subtype_id') or [False, ''])[0] == note_id
            if 'published_date_str' in properties_names and values.get('date'):
                values['published_date_str'] = format_datetime(self.env, values['date'])
        return vals_list

    def _portal_message_format_attachments(self, attachment_values):
        """ From 'attachment_values' (dict coming from reading 'ir.attachment')
        get an updated version formatted for frontend display. """
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        attachment_values['filename'] = attachment_values['name']
        attachment_values['mimetype'] = (
            'application/octet-stream' if safari and
            'video' in (attachment_values["mimetype"] or "")
            else attachment_values["mimetype"])
        return attachment_values
