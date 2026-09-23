import stdnum.de.stnr
import stdnum.exceptions

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_de_config_id = fields.Many2one(
        comodel_name="l10n_de.config",
        compute="_compute_l10n_de_config_id",
        search="_search_l10n_de_config_id",
    )

    l10n_de_stnr = fields.Char(
        related="l10n_de_config_id.l10n_de_stnr",
        readonly=False,
    )
    l10n_de_widnr = fields.Char(
        related="l10n_de_config_id.l10n_de_widnr",
        readonly=False,
    )

    def _search_l10n_de_config_id(self, operator, value):
        return self._search_config_link("l10n_de.config", operator, value)

    def _compute_l10n_de_config_id(self):
        configs = self.env["l10n_de.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_de_config_id = by_company.get(company.id, False)

    def get_l10n_de_stnr_national(self):
        self.check_singleton()
        national_steuer_nummer = None

        if self.l10n_de_config_id.l10n_de_stnr and self.country_code == "DE":
            try:
                national_steuer_nummer = stdnum.de.stnr.to_country_number(
                    self.l10n_de_config_id.l10n_de_stnr, self.state_id.name
                )
            except stdnum.exceptions.InvalidComponent:
                raise ValidationError(
                    _("Your company's SteuerNummer is not compatible with your state")
                ) from None
            except stdnum.exceptions.InvalidFormat:
                if stdnum.de.stnr.is_valid(
                    self.l10n_de_config_id.l10n_de_stnr, self.state_id.name
                ):
                    national_steuer_nummer = self.l10n_de_config_id.l10n_de_stnr
                else:
                    raise ValidationError(
                        _("Your company's SteuerNummer is not valid")
                    ) from None

        elif self.l10n_de_config_id.l10n_de_stnr:
            national_steuer_nummer = self.l10n_de_config_id.l10n_de_stnr

        return national_steuer_nummer
