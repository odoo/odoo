# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


class MailInboxController(WebclientController):

    @classmethod
    def _process_request_for_internal_user(self, store: Store, name, params):
        super()._process_request_for_internal_user(store, name, params)
        if name == 'fetchmail_inbox':
            folder = (params or {}).get('folder', 'new')
            domain = self._fetchmail_inbox_domain(folder)
            mails = request.env['fetchmail.mail'].search(domain, order='date desc', limit=50)
            if mails:
                store.add(mails, '_store_fetchmail_mail_fields')
            store.add_global_values(
                fetchmail_inbox={
                    'folder': folder,
                    'mail_ids': mails.ids,
                }
            )

    @classmethod
    def _fetchmail_inbox_domain(cls, folder):
        base = [('fetchmail_server_id.user_id', '=', request.env.uid)]
        if folder == 'new':
            return base + [('mail_type', '=', 'incoming'), ('mail_status', '=', 'new')]
        if folder == 'starred':
            return base + [('is_starred', '=', True)]
        if folder == 'draft':
            return base + [('mail_type', '=', 'outgoing'), ('mail_status', '=', 'draft')]
        if folder == 'sent':
            return base + [('mail_type', '=', 'outgoing'), ('mail_status', '=', 'sent')]
        if folder == 'scheduled':
            from odoo import fields
            return base + [
                ('mail_type', '=', 'outgoing'),
                ('mail_status', '=', 'outgoing'),
                ('date', '>', fields.Datetime.now()),
            ]
        return base
