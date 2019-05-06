# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_latam_use_documents = fields.Boolean(
        compute='_compute_l10n_latam_use_documents',
        string='Use Documents?',
    )

    def _compute_l10n_latam_use_documents(self):
        for rec in self:
            rec.l10n_latam_use_documents = \
                rec._localization_use_documents()

    def _localization_use_documents(self):
        """ This method is to be inherited by localizations and return
        True if localization use documents
        """
        self.ensure_one()
        return False
