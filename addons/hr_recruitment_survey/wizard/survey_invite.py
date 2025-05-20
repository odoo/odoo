# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models
from odoo.fields import Domain


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    def _get_existing_answers_domain(self, partners, emails):
        return Domain.AND([
            Domain('state', '!=', 'cancelled'),
            super()._get_existing_answers_domain(partners, emails),
        ])
