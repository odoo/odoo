# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_ar_afip_responsability_type = fields.Selection(
        related='move_id.l10n_ar_afip_responsability_type',
    )
