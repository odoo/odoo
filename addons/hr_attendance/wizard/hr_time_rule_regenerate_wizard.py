# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRuleRegenerateWizard(models.TransientModel):
    _inherit = 'hr.time.rule.regenerate.wizard'

    source_model_filter = fields.Selection(
        selection_add=[('hr.attendance', 'Attendances only')],
        ondelete={'hr.attendance': 'set default'},
    )
