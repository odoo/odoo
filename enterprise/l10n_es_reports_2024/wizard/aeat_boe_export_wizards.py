# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Mod303BOEWizard(models.TransientModel):
    _inherit = 'l10n_es_reports.aeat.boe.mod303.export.wizard'

    # Rename according to the changes in Orden HAC/819/2024 (https://www.boe.es/eli/es/o/2024/07/30/hac819)
    complementary_declaration = fields.Boolean(
        string="Corrective Self-Assessment",
        help="Whether or not this BOE file is a corrective self-assessment."
    )

    rectification_direct_debit = fields.Boolean(
        string="As a result of the presentation of the corrective self-assessment, I request to cancel/modify the direct debit made"
    )
    rectification_motive_rectifications = fields.Boolean(string="Rectifications (except those included in the following reason)")
    rectification_motive_discrepancy_adm_crit = fields.Boolean(string="Administrative criteria discrepancy")
