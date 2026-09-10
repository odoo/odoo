from odoo import models


class SmsComposer(models.TransientModel):
    _inherit = 'sms.composer'

    def _action_send_sms_comment_prepare_values(self):
        values = super()._action_send_sms_comment_prepare_values()
        values['source_sms_template_id'] = self.template_id.id
        return values

    def _prepare_mass_log_values(self, records, sms_records_values):
        values = super()._prepare_mass_log_values(records, sms_records_values)
        values['source_sms_template_id'] = self.template_id.id
        return values
