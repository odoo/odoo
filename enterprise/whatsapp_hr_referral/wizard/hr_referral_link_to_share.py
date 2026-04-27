# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrReferralLinkToShare(models.TransientModel):
    _inherit = 'hr.referral.link.to.share'

    recipient = fields.Char(string="Recipient")

    def _get_whatsapp_safe_fields(self):
        return {'job_id.name', 'job_id.company_id.name', 'url', 'recipient'}
