# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends('phone_sanitized')
    def _compute_mailing_contact_id(self):
        return super()._compute_mailing_contact_id()
