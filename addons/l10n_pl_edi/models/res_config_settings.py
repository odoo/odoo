# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_mode = fields.Selection(
        [('test', 'Test (experimental)'), ('prod', 'Official')],
        compute='_compute_l10n_pl_edi_mode',
        inverse='_set_l10n_pl_edi_register_mode',
        readonly=False,
        string="KSeF Environment",
    )
