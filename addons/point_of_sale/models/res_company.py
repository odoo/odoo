from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.pos.load"]

    point_of_sale_config_id = fields.Many2one(
        comodel_name="point_of_sale.config",
        compute="_compute_point_of_sale_config_id",
        search="_search_point_of_sale_config_id",
    )

    point_of_sale_use_ticket_qr_code = fields.Boolean(
        related="point_of_sale_config_id.point_of_sale_use_ticket_qr_code",
    )
    point_of_sale_ticket_unique_code = fields.Boolean(
        related="point_of_sale_config_id.point_of_sale_ticket_unique_code",
    )
    point_of_sale_ticket_portal_url_display_mode = fields.Selection(
        related="point_of_sale_config_id.point_of_sale_ticket_portal_url_display_mode",
    )

    def _search_point_of_sale_config_id(self, operator, value):
        return self._search_config_link("point_of_sale.config", operator, value)

    def _compute_point_of_sale_config_id(self):
        configs = self.env["point_of_sale.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.point_of_sale_config_id = by_company.get(company.id, False)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "=", config.company_id.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "currency_id",
            "email",
            "website",
            "company_registry",
            "vat",
            "name",
            "phone_ids",
            "partner_id",
            "country_id",
            "state_id",
            "street",
            "city",
            "zip",
            "tax_calculation_rounding_method",
            "account_fiscal_country_id",
            "nomenclature_id",
            "point_of_sale_use_ticket_qr_code",
            "point_of_sale_ticket_unique_code",
            "point_of_sale_ticket_portal_url_display_mode",
        ]

    @api.constrains(
        "account_config_id.fiscalyear_lock_date",
        "account_config_id.tax_lock_date",
        "account_config_id.sale_lock_date",
        "account_config_id.hard_lock_date",
    )
    def check_lock_dates(self):
        pos_session_model = self.env["pos.session"].sudo()
        for record in self:
            record = record.with_context(ignore_exceptions=True)
            fiscal_lock_date = max(
                record.account_config_id.user_fiscalyear_lock_date,
                record.account_config_id.user_hard_lock_date,
            )
            sessions_in_period = pos_session_model.search(
                Domain("company_id", "child_of", record.id)
                & Domain("state", "!=", "closed")
                & Domain.OR(
                    (
                        Domain("start_at", "<=", fiscal_lock_date),
                        Domain(
                            "start_at",
                            "<=",
                            record.account_config_id.user_tax_lock_date,
                        ),
                        Domain("config_id.journal_id.type", "=", "sale")
                        & Domain(
                            "start_at",
                            "<=",
                            record.account_config_id.user_sale_lock_date,
                        ),
                    )
                )
            )
            if sessions_in_period:
                dbg.logic.debug(
                    "lock date on company %s refused by open sessions %s",
                    record.id,
                    dbg.rec(sessions_in_period),
                )
                sessions_str = ", ".join(sessions_in_period.mapped("name"))
                raise ValidationError(
                    self.env._(
                        "Please close all the point of sale sessions in this period before closing it. Open sessions are: %s ",
                        sessions_str,
                    )
                )
