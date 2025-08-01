from odoo import fields, models, api


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    sms_twilio_sid = fields.Char(related="sms_tracker_id.sms_twilio_sid", depends=['sms_tracker_id'])
    record_company_id = fields.Many2one('res.company', 'Company', ondelete='set null')

    def _get_sms_company(self):
        return self.mail_message_id.record_company_id or self.record_company_id or super()._get_sms_company()

    def _get_batch_size(self):
        company_id = self._get_sms_company()
        if company_id and company_id.sms_provider == 'twilio':
            return int(self.env['ir.config_parameter'].sudo().get_param('sms_twilio.session.batch.size', 10))
        return super()._get_batch_size()

    def _handle_call_result_hook(self, results):
        """
        Store the sid of Twilio on the SMS tracking record (as SMS will be deleted)
        :param results: a list of dict in the form [{
            'uuid': Odoo's id of the SMS,
            'state': State of the SMS in Odoo,
            'sms_twilio_sid': Twilio's id of the SMS,
        }, ...]
        """
        if self._get_sms_company().sms_provider != 'twilio':
            return
        grouped_self = self.grouped("uuid")
        for result in results:
            sms = grouped_self.get(result.get('uuid'))
            if sms and sms.sms_tracker_id and result.get('sms_twilio_sid'):
                sms.sms_tracker_id.sms_twilio_sid = result['sms_twilio_sid']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['record_company_id'] = vals.get('record_company_id') or self.env.company.id  # TODO RIGR in master: move this field to SmsSms, and populate it via vals_list from all flows
        return super().create(vals_list)
