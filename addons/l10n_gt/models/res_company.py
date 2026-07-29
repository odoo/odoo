# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gt_isr_withholding_agent = fields.Boolean(
        related='partner_id.l10n_gt_isr_withholding_agent',
        readonly=False,
    )
    l10n_gt_vat_withholding_type = fields.Selection(
        related='partner_id.l10n_gt_vat_withholding_type',
        readonly=False,
    )
