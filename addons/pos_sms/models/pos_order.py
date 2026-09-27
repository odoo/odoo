from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_sms_receipt_template(self):
        if self.config_id.module_pos_sms:
            return self.config_id.sms_receipt_template_id
        return False

    def action_sent_message_on_sms(self, phone, template=None):
        self.ensure_one()
        receipt_template = template or self._get_sms_receipt_template()
        if not receipt_template or not phone:
            return
        sms_composer = self.env['sms.composer'].with_context(active_id=self.id).create(
            {
                'composition_mode': 'comment',
                'numbers': phone,
                'recipient_single_number_itf': phone,
                'template_id': receipt_template.id,
                'res_model': 'pos.order'
            }
        )
        self.mobile = phone
        sms_composer.action_send_sms()
