# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_br_is_icbs = fields.Boolean(
        related='company_id.l10n_br_is_icbs',
        readonly=False,
    )
    l10n_br_is_cbs_ibs_taxpayer = fields.Boolean(
        related='company_id.partner_id.l10n_br_is_cbs_ibs_taxpayer',
        readonly=False,
    )
    l10n_br_is_cbs_ibs_normal = fields.Boolean(
        related='company_id.partner_id.l10n_br_is_cbs_ibs_normal',
        readonly=False,
    )
    l10n_br_cbs_credit = fields.Float(
        related='company_id.partner_id.l10n_br_cbs_credit',
        readonly=False,
    )
    l10n_br_ibs_credit = fields.Float(
        related='company_id.partner_id.l10n_br_ibs_credit',
        readonly=False,
    )
