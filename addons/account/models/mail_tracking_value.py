# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailTrackingValue(models.Model):
    _inherit = 'mail.tracking.value'

    @api.ondelete(at_uninstall=True)
    def _except_audit_log(self):
        self.mail_message_id._except_audit_log()

    def write(self, vals):
        self._except_audit_log()
        return super().write(vals)

    @api.model
    def _create_tracking_values(self, initial_value, new_value, col_name, col_info, record):
        if self.env.context.get('display_account_trust') and isinstance(record[col_name], self.env.registry['res.partner.bank']):
            initial_value = initial_value.with_context(display_account_trust=False)
            new_value = new_value.with_context(display_account_trust=False)
        return super()._create_tracking_values(initial_value, new_value, col_name, col_info, record)
