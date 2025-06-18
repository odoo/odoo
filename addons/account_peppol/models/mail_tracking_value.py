from odoo import models


class MailTrackingValue(models.Model):
    _inherit = 'mail.tracking.value'

    def _create_tracking_values(self, initial_value, new_value, col_name, col_info, record):
        # EXTENDS mail.tracking.value
        values = super()._create_tracking_values(initial_value, new_value, col_name, col_info, record)
        if (col_name == 'peppol_eas'):
            values['old_value_char'] += f' ({initial_value})'
            values['new_value_char'] += f' ({new_value})'
        return values
