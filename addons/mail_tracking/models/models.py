from odoo import fields, models


class MailBase(models.AbstractModel):
    _inherit = 'base'

    def _prepare_tracking_vals(self, initial_value, new_value, col_name, col_info):
        res = super()._prepare_tracking_vals(initial_value, new_value, col_name, col_info)
        tracking_vals = self.env['mail.tracking.value']._create_tracking_values(
            initial_value, new_value, col_name, col_info, self
        )
        res['tracking_value_ids'] = [fields.Command.create(tracking_vals)]
        return res
