# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_edi_predial_account = fields.Char(string="Cuenta predial", size=150)

    @api.constrains('l10n_mx_edi_predial_account')
    def _check_l10n_mx_edi_predial_account(self):
        for record in self:
            if record.l10n_mx_edi_predial_account and not re.fullmatch(r"[0-9a-zA-Z]{1,150}", record.l10n_mx_edi_predial_account):
                raise ValidationError(_("Cuenta predial should be alphanumeric!"))
