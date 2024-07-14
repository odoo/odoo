from odoo import models, fields, _
from odoo.tools import format_date

# Used for printing a field service report

class Task(models.Model):
    _inherit = 'project.task'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = [
                (_("Date:"), format_date(self.env, fields.Date.today()))
            ]
