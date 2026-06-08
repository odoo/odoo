# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_reference_work_entry_type = fields.Many2one(
        'hr.work.entry.type',
        related='company_id.l10n_fr_reference_work_entry_type',
        readonly=False)
