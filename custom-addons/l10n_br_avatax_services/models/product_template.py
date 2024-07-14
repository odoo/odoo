# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _l10n_br_property_service_code_origin_id_domain(self):
        return [("city_id", "=", self.env.company.partner_id.city_id.id)]

    l10n_br_property_service_code_origin_id = fields.Many2one(
        "l10n_br.service.code",
        domain=_l10n_br_property_service_code_origin_id_domain,
        string="Service Code Origin",
        company_dependent=True,
        help="Brazil: City service code where the provider is registered.",
    )
    l10n_br_labor = fields.Boolean(
        "Labor Assignment", help="Brazil: If your service involves labor, select this checkbox."
    )
    l10n_br_service_code_ids = fields.Many2many(
        "l10n_br.service.code",
        string="Service Codes",
        help="Brazil: The service codes for this product, as defined by the cities in which you wish to sell it. If no city-specific code is provided, the Service Code Origin will be used instead.",
    )
    l10n_br_company_city_id = fields.Many2one(
        "res.city",
        compute="_compute_l10n_br_company_city_id",
        help="Technical field used to determined the default of a service code when configured as a service code origin.",
    )

    @api.constrains("l10n_br_service_code_ids")
    def _check_l10n_br_service_code_ids(self):
        for product in self:
            for (_company, city), codes in product.l10n_br_service_code_ids.grouped(lambda code: (code.company_id, code.city_id)).items():
                if len(codes) > 1:
                    raise ValidationError(_("Can't have more than one service code for %s.", city.display_name))

    @api.depends("company_id")
    @api.depends_context("company")
    def _compute_l10n_br_company_city_id(self):
        for product in self:
            company = product.company_id or self.env.company
            product.l10n_br_company_city_id = company.partner_id.city_id

    def _l10n_br_is_only_allowed_on_service_invoice(self):
        """Service products are only allowed on a goods invoice if it's a transportation service."""
        return not self.l10n_br_transport_cost_type and self.type == "service"
