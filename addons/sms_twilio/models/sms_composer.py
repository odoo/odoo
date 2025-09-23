from odoo import models


class SendSMS(models.TransientModel):
    _inherit = 'sms.composer'

    def _prepare_mass_sms_values(self, records):
        results = super()._prepare_mass_sms_values(records)
        for record, result in zip(records, results):
            company = self.env.company
            if "company_id" in record._fields:
                company = record.company_id
            elif "record_company_id" in record._fields:
                company = record.record_company_id
            results[record.id]["record_company_id"] = company.id
        return results
