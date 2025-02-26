from odoo.addons.mail.tools.discuss import Store

from odoo import api, fields, models, tools


class MailMessage(models.Model):
    _inherit = 'mail.message'

    mailing_trace_ids = fields.One2many('mailing.trace', 'mail_message_id')

    def _to_store_defaults(self, *args, **kwargs):
        return super()._to_store_defaults(*args, **kwargs) + ['mailing_name']

    def _to_store(self, store, fields, *args, **kwargs):
        super()._to_store(store, [field for field in fields if field != 'mailing_name'], *args, **kwargs)
        if 'mailing_name' not in fields:
            return
        for message in self:
            store.add(message, {'mailing_name': message.mailing_trace_ids.mass_mailing_id.name})
