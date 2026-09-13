from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ke_oscu_is_active = fields.Boolean(
        string="Is OSCU active?",
        compute="_compute_l10n_ke_oscu_is_active",
        help="Whether this company is set up for OSCU flows.",
    )

    def _compute_l10n_ke_oscu_is_active(self):
        """Overridden in enterprise when the OSCU module is used in the company"""
        self.l10n_ke_oscu_is_active = False
