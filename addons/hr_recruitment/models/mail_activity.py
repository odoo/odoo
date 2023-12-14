# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class MailActivityModel(models.Model):
    _inherit = "mail.activity"

    def _get_phone_numbers_by_activity(self):
        result = super(MailActivityModel, self)._get_phone_numbers_by_activity()
        data_by_model = self._classify_by_model()
        for model, data in data_by_model.items():
            records = self.env[model].browse(data["record_ids"])
            for record, activity in zip(records, data["activities"]):
                if not result[activity].get('mobile') and not result[activity].get('phone'):
                    mobile = record.partner_mobile if 'partner_mobile' in record else False
                    phone = record.partner_phone if 'partner_phone' in record else False
                    result[activity] = {"mobile": mobile, "phone": phone}
        return result
