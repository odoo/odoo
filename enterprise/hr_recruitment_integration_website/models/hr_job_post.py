# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class JobPost(models.Model):
    _inherit = 'hr.job.post'

    apply_method = fields.Selection(
        selection_add=[('redirect', 'Redirect to Website')],
        ondelete={'redirect': 'cascade'},
    )

    def _contact_point_to_vector(self):
        self.ensure_one()
        if self.apply_method == 'redirect':
            return 'job_apply_url'
        return super()._contact_point_to_vector()
