# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gt_vat_affiliation = fields.Selection(
        related='partner_id.l10n_gt_vat_affiliation',
        readonly=False,
    )
