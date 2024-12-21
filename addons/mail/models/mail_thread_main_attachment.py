# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class MailThreadMainAttachment(models.AbstractModel):
    """ Mixin that adds main attachment support to the MailThread class. """

    _name = 'mail.thread.main.attachment'
    _inherit = ['mail.thread']
    _description = 'Mail Main Attachment management'

    message_main_attachment_id = fields.Many2one(string="Main Attachment", comodel_name='ir.attachment', copy=False, index='btree_not_null')

    def _message_post_after_hook(self, message, msg_values):
        """ Set main attachment field if necessary """
        super()._message_post_after_hook(message, msg_values)
        self.sudo()._message_set_main_attachment_id(
            self.env["ir.attachment"].browse([
                attachment_command[1]
                for attachment_command in (msg_values['attachment_ids'] or [])
            ])
        )

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        """ Update 'main' attachment.

        :param list attachments: new main attachment IDS; if several attachments
          are given, we search for pdf or image first;
        :param boolean force: if set, replace an existing attachment; otherwise
          update is skipped;
        :param filter_xml: filters out xml (and octet-stream) attachments, as in
          most cases you don't want that kind of file to end up as main attachment
          of records;
        """
        if attachments and (force or not self.message_main_attachment_id):
            # we filter out attachment with 'xml' and 'octet' types
            if filter_xml:
                attachments = attachments.filtered(
                    lambda r: not r.mimetype.endswith('xml') and not r.mimetype.endswith('application/octet-stream')
                )

            # Assign one of the attachments as the main according to the following priority: pdf, image, other types.
            if attachments:
                self.with_context(tracking_disable=True).message_main_attachment_id = max(
                    attachments,
                    key=lambda r: (r.mimetype.endswith('pdf'), r.mimetype.startswith('image'))
                ).id

    def _thread_to_store(self, store: Store, fields, *, request_list=None):
        super()._thread_to_store(store, fields, request_list=request_list)
        if request_list and "attachments" in request_list:
            store.add(
                self,
                Store.One("message_main_attachment_id", [], rename="mainAttachment"),
                as_thread=True,
            )
