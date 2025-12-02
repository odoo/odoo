# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import format_datetime, groupby


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _compute_is_current_user_or_guest_author(self):
        super()._compute_is_current_user_or_guest_author()
        portal_data = self.env.context.get("portal_data", {})
        portal_partner = portal_data.get("portal_partner")
        portal_thread = portal_data.get("portal_thread")
        if (
            not portal_partner
            or not portal_thread
            or not isinstance(portal_partner, self.pool["res.partner"])
            or not isinstance(portal_thread, self.pool["mail.thread"])
        ):
            return
        for message in self:
            if (
                message.author_id == portal_partner
                and message.model == portal_thread._name
                and message.res_id == portal_thread.id
            ):
                message.is_current_user_or_guest_author = True

    def portal_message_format(self, options=None):
        """ Simpler and portal-oriented version of 'message_format'. Purpose
        is to prepare, organize and format values required by frontend widget
        (frontend Chatter).

        This public API asks for read access on messages before doing the
        actual computation in the private implementation.

        :param dict options: options, used notably for inheritance and adding
          specific fields or properties to compute;

        :returns: list of dict, one per message in self. Each dict contains
          values for either fields, either properties derived from fields.
        :rtype: list[dict]
        """
        self.check_access('read')
        return self._portal_message_format(
            self._portal_get_default_format_properties_names(options=options),
            options=options,
        )

    def _portal_get_default_format_properties_names(self, options=None):
        """ Fields and values to compute for portal format.

        :param dict options: options, used notably for inheritance and adding
          specific fields or properties to compute;

        :returns: fields or properties derived from fields
        :rtype: set
        """
        return {
            'attachment_ids',
            'author_avatar_url',
            'author_id',
            'author_guest_id',
            'body',
            'date',
            'id',
            'is_internal',
            'is_message_subtype_note',
            'message_type',
            'model',
            'published_date_str',
            'res_id',
            'starred',
            'subtype_id',
        }

    def _portal_message_format(self, properties_names, options=None):
        """ Format messages for portal frontend. This private implementation
        does not check for access that should be checked beforehand.

        Notes:
          * when asking for attachments: ensure an access token is present then
            access them (using sudo);

        :param set properties_names: fields or properties derived from fields
          for which we are going to compute values;

        :returns: list of dict, one per message in self. Each dict contains
          values for either fields, either properties derived from fields.
        :rtype: list[dict]
        """
        message_to_attachments = {}
        if 'attachment_ids' in properties_names:
            properties_names.remove('attachment_ids')
            attachments_sudo = self.sudo().attachment_ids
            related_attachments = {
                att_read_values['id']: att_read_values
                for att_read_values in attachments_sudo.read(
                    ["checksum", "id", "mimetype", "name", "res_id", "res_model"]
                )
            }
            message_to_attachments = {
                message.id: [
                    message._portal_message_format_attachments(related_attachments[att_id])
                    for att_id in message.attachment_ids.ids
                ]
                for message in self.sudo()
            }

        fnames = {
            property_name for property_name in properties_names
            if property_name in self._fields
        }
        vals_list = self._read_format(fnames)

        note_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        for message, values in zip(self, vals_list):
            values["body"] = ["markup", values["body"]]
            if message_to_attachments:
                values['attachment_ids'] = message_to_attachments.get(message.id, {})
            if 'author_avatar_url' in properties_names:
                if options and options.get("token"):
                    values['author_avatar_url'] = f'/mail/avatar/mail.message/{message.id}/author_avatar/50x50?access_token={options["token"]}'
                elif options and options.get("hash") and options.get("pid"):
                    values['author_avatar_url'] = f'/mail/avatar/mail.message/{message.id}/author_avatar/50x50?_hash={options["hash"]}&pid={options["pid"]}'
                else:
                    values['author_avatar_url'] = f'/web/image/mail.message/{message.id}/author_avatar/50x50'
            if 'is_message_subtype_note' in properties_names:
                values['is_message_subtype_note'] = (values.get('subtype_id') or [False, ''])[0] == note_id
            if 'published_date_str' in properties_names:
                values['published_date_str'] = format_datetime(self.env, values['date']) if values.get('date') else ''
            reaction_groups = []
            for content, reactions in groupby(message.sudo().reaction_ids, lambda r: r.content):
                reactions = self.env["mail.message.reaction"].union(*reactions)
                reaction_groups.append(
                    {
                        "content": content,
                        "count": len(reactions),
                        "guests": [
                            {"id": guest.id, "name": guest.name}
                            for guest in reactions.guest_id
                        ],
                        "message": message.id,
                        "partners": [
                            # sudo: res.partner - reading partners of reaction on accessible message is allowed
                            {"id": partner.id, "name": partner.name}
                            for partner in reactions.partner_id.sudo()
                        ],
                    },
                )
            values.update(
                {
                    "reactions": reaction_groups,
                    "author_id": {
                        "id": message.author_id.id,
                        "name": message.author_id.name,
                    },
                    "thread": {"model": values["model"], "id": values["res_id"]},
                }
            )
        return vals_list

    def _portal_message_format_attachments(self, attachment_values):
        """ From 'attachment_values' get an updated version formatted for
        frontend display.

        :param dict attachment_values: values coming from reading attachments
          in database;

        :returns: updated attachment_values
        :rtype: dict
        """
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        attachment_values['filename'] = attachment_values['name']
        attachment_values['mimetype'] = (
            'application/octet-stream' if safari and
            'video' in (attachment_values["mimetype"] or "")
            else attachment_values["mimetype"])
        attachment = self.env['ir.attachment'].browse(attachment_values['id'])
        attachment_values["raw_access_token"] = attachment._get_raw_access_token()
        if self.is_current_user_or_guest_author:
            attachment_values["ownership_token"] = attachment._get_ownership_token()
        return attachment_values
