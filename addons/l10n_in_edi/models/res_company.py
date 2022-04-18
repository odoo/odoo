# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_edi_username = fields.Char("E-invoice (IN) Username", groups="base.group_system")
    l10n_in_edi_password = fields.Char("E-invoice (IN) Password", groups="base.group_system")
    l10n_in_edi_token = fields.Char("E-invoice (IN) Token", groups="base.group_system")
    l10n_in_edi_token_validity = fields.Datetime("E-invoice (IN) Valid Until", groups="base.group_system")
    l10n_in_edi_production_env = fields.Boolean(
        string="E-invoice (IN) Is production OSE environment",
        help="Enable the use of production credentials",
        groups="base.group_system",
    )

    def _l10n_in_edi_token_is_valid(self):
        self.ensure_one()
        if self.l10n_in_edi_token and self.l10n_in_edi_token_validity > fields.Datetime.now():
            return True
        return False

    def _neutralize(self):
        super()._neutralize()
        self.flush()
        self.invalidate_cache()
        self.env.cr.execute("""UPDATE res_company SET
            l10n_in_edi_production_env = false,
            l10n_in_edi_username = Null,
            l10n_in_edi_password = Null,
            l10n_in_edi_token = Null,
            l10n_in_edi_token_validity = Null
        """)
