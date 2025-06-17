from odoo import fields, models


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    sms_twilio_sid = fields.Char(related="sms_tracker_id.sms_twilio_sid", depends=['sms_tracker_id'])

    def _get_batch_size(self):
        if self.mail_message_id and self.mail_message_id.record_company_id and self.mail_message_id.record_company_id.sms_provider == 'twilio':
            return int(self.env['ir.config_parameter'].sudo().get_param('sms_twilio.session.batch.size', 10))
        return super()._get_batch_size()

    def _handle_call_result_hook(self, company, results):
        # Store the sid of Twilio on the SMS tracking record (as SMS will be deleted)
        if company.sms_provider != 'twilio':
            return
        grouped_self = self.grouped("uuid")
        for result in results:
            sms = grouped_self.get(result.get('uuid'))
            if sms and sms.sms_tracker_id and result.get('sms_twilio_sid'):
                sms.sms_tracker_id.sms_twilio_sid = result['sms_twilio_sid']
