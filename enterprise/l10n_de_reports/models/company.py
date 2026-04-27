# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Adding the fields as company_dependent does not break stable policy
    l10n_de_datev_consultant_number = fields.Char(company_dependent=True)
    l10n_de_datev_client_number = fields.Char(company_dependent=True)
    l10n_de_datev_account_length = fields.Integer(
        string="DateV G/L account length",
        default=8,
    )

    @api.constrains('l10n_de_datev_account_length')
    def _validate_l10n_de_datev_account_length(self):
        for company in self:
            if not (4 <= company.l10n_de_datev_account_length <= 8):
                raise ValidationError(_("G/L account length must be between 4 and 8."))
