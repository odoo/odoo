# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    @api.model
    def _selection_template_model(self):
        return super()._selection_template_model() + [('whatsapp.template', 'WhatsApp')]

    notification_type = fields.Selection(selection_add=[('whatsapp', 'WhatsApp')], ondelete={'whatsapp': 'set default'})

    def _compute_template_model_id(self):
        whatsapp_model = self.env['ir.model']._get('whatsapp.template')
        whatsapp_mails = self.filtered(lambda mail: mail.notification_type == 'whatsapp')
        whatsapp_mails.template_model_id = whatsapp_model
        super(EventTypeMail, self - whatsapp_mails)._compute_template_model_id()
