from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mitid_kyc_status = fields.Selection(related='company_id.mitid_kyc_status')
