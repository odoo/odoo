from odoo import fields, models


class ResCompany(models.CachedModel):
    _inherit = 'res.company'

    bank_ids = fields.One2many(related='partner_id.bank_ids', readonly=False)
