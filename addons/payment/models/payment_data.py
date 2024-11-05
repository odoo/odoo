# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentData(models.Model):
    _description = "Payment Data"

    provider_code = fields.Char(required=True)
    payload = fields.Json(string="Payload", required=True)

    def _cron_process(self):
        """ Trigger the processing of payment data to update the transaction.

        :return: None
        """
        data_to_process = self
        if not data_to_process:
            data_to_process = self.env['payment.data'].search([])

        for payment_data in data_to_process:
            payment_data = payment_data[0]  # Avoid pre-fetching after each cache invalidation.
            self.env['payment.transaction']._handle_notification_data(
                payment_data.provider_code, payment_data.payload, postpone=False
            )
            payment_data.unlink()
            self.env.cr.commit()  # Commit to mitigate an eventual cron kill.
