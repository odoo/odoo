import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_ge_edi.tools.rsge_client import RSgeClient, RSgeError, translate_rsge_error


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ge_edi_su = fields.Char(string="RS.ge Service User", groups="base.group_system")
    l10n_ge_edi_sp = fields.Char(string="RS.ge Service Password", groups="base.group_system")
    l10n_ge_edi_user_id = fields.Integer(
        string="RS.ge User Id",
        groups="base.group_system",
        readonly=True,
        compute="_compute_l10n_ge_edi_user_id",
        store=True,
    )

    @api.depends("l10n_ge_edi_su", "l10n_ge_edi_sp")
    def _compute_l10n_ge_edi_user_id(self):
        for company in self:
            if not company.l10n_ge_edi_su or not company.l10n_ge_edi_sp:
                company.l10n_ge_edi_user_id = False
                continue
            try:
                company.l10n_ge_edi_user_id = company._l10n_ge_edi_get_client().check_credentials()
            except (RSgeError, UserError):  # a stored compute must never raise, e.g. on module update
                company.l10n_ge_edi_user_id = False

    @api.constrains("l10n_ge_edi_su")
    def _check_l10n_ge_edi_su(self):
        for company in self:
            if company.l10n_ge_edi_su and not re.match(r"^\S+:\d+$", company.l10n_ge_edi_su):
                raise ValidationError(
                    self.env._(
                        'The RS.ge Service User must be in the "username:number" format shown on '
                        "the RS.ge sub-user page.",
                    ),
                )

    def _l10n_ge_edi_get_client(self):
        self.ensure_one()
        company = self.sudo()
        try:
            return RSgeClient(su=company.l10n_ge_edi_su, sp=company.l10n_ge_edi_sp)
        except RSgeError as error:
            raise UserError(translate_rsge_error(self.env, error)) from error
