from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_rs_edi_registration_number = fields.Char(
        string="Registration Number",
        size=13,
        help="Company ID ( Matični Broj ) assigned by the Serbian Business Registers Agency (APR) ",
    )
    l10n_rs_edi_public_funds = fields.Char(
        string="JBKJS",
        size=5,
        help="Unique Identifier of Public Funds Users such as Government agencies, public institutions and state-owned enterprises.",
    )

    @api.constrains("l10n_rs_edi_public_funds")
    def _check_l10n_rs_edi_public_funds(self):
        for record in self:
            if record.l10n_rs_edi_public_funds and (
                len(record.l10n_rs_edi_public_funds) < 5
                or not record.l10n_rs_edi_public_funds.isdigit()
            ):
                raise ValidationError(
                    _("Public Funds ID(JBKJS) must be exactly five digits")
                )

    @api.constrains("l10n_rs_edi_registration_number")
    def _check_l10n_rs_edi_registration_number(self):
        for record in self:
            if record.l10n_rs_edi_registration_number and (
                len(record.l10n_rs_edi_registration_number) not in [8, 13]
                or not record.l10n_rs_edi_registration_number.isdigit()
            ):
                raise ValidationError(
                    _("Customer identification number should be 8 or 13 digits")
                )
