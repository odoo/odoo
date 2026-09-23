from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_fr_hr_holidays_config_id = fields.Many2one(
        comodel_name="l10n_fr_hr_holidays.config",
        compute="_compute_l10n_fr_hr_holidays_config_id",
        search="_search_l10n_fr_hr_holidays_config_id",
    )

    def _search_l10n_fr_hr_holidays_config_id(self, operator, value):
        return self._search_config_link("l10n_fr_hr_holidays.config", operator, value)

    def _compute_l10n_fr_hr_holidays_config_id(self):
        configs = self.env["l10n_fr_hr_holidays.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_fr_hr_holidays_config_id = by_company.get(company.id, False)

    def _get_fr_reference_leave_type(self):
        self.check_singleton()
        if not self.l10n_fr_hr_holidays_config_id.l10n_fr_reference_leave_type:
            _debug.logic(
                "fr_reference_leave_type_missing",
                reason="not_configured",
                company=self,
            )
            raise ValidationError(
                self.env._(
                    "You must first define a reference time off type for the company."
                )
            )
        return self.l10n_fr_hr_holidays_config_id.l10n_fr_reference_leave_type
