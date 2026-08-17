# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ph_branch_code = fields.Char(string='Company Branch Code', related='partner_id.l10n_ph_branch_code')
    l10n_ph_rdo = fields.Char("RDO", help="Revenue District Office")

    def _l10n_ph_is_vat_registered(self):
        """ `l10n_ph_is_vat_registered` is defined by `l10n_ph_reports`, which this module cannot depend on. """
        return 'l10n_ph_is_vat_registered' in self._fields and self.l10n_ph_is_vat_registered
