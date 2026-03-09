

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def _get_send_email_binding_excluded_models(self):
        return super()._get_send_email_binding_excluded_models() + ['hr.applicant']
