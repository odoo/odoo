# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    batch_payroll_move_lines = fields.Boolean(
        related='company_id.batch_payroll_move_lines',
        string="Batch Payroll Move Lines", readonly=False,
        help="Enable this option to merge all the accounting entries for the same period into a single account move line. This will anonymize the accounting entries but also disable single payment generations."
    )
