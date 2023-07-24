from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ca_pst = fields.Char(related='partner_id.l10n_ca_pst', string='PST Number', store=False, readonly=False)
