from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.website.models import ir_http


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _default_website_id(self):
        company_id = self.env.company.id

        if self.env.context.get("default_company_id"):
            company_id = self.env.context.get("default_company_id")

        domain = [("company_id", "=", company_id)]
        return self.env["website"].search(domain, limit=1)

    website_id = fields.Many2one(
        comodel_name="website",
        default=_default_website_id,
        domain="[('company_id', '=?', company_id)]",
        ondelete="restrict",
        tracking=20,
        help="If you want a pricelist to be available on a website,"
        "you must fill in this field or make it selectable."
        "Otherwise, the pricelist will not apply to any website.",
    )
    code = fields.Char(
        string="E-commerce Promotional Code",
        groups="base.group_user",
    )
    selectable = fields.Boolean(help="Allow the end user to choose this price list")

    @api.constrains("company_id", "website_id")
    def _check_websites_in_company(self):
        for record in self.filtered(lambda pl: pl.website_id and pl.company_id):
            if record.website_id.company_id != record.company_id:
                raise ValidationError(
                    _(
                        "Only the company's websites are allowed."
                        "\nLeave the Company field empty or select a website from that company."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("company_id") and not vals.get("website_id"):
                self = self.with_context(default_company_id=vals["company_id"])
        pricelists = super().create(vals_list)
        if pricelists:
            self.env.registry.clear_cache()
        return pricelists

    def write(self, vals):
        res = super().write(vals)
        self and self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self and self.env.registry.clear_cache()
        return res

    def _get_domain_partner_pricelist_multi_search(self, company_id):
        domain = super()._get_domain_partner_pricelist_multi_search(company_id)
        website = ir_http.get_request_website()
        if website:
            domain += self._get_domain_website_pricelists(website)
        return domain

    def _filtered_partner_pricelist_multi(self):
        res = super()._filtered_partner_pricelist_multi()
        website = ir_http.get_request_website()
        if website:
            res = res.filtered(lambda pl: pl._is_available_on_website(website))
        return res

    def _is_available_on_website(self, website):
        self.check_singleton()
        if self.company_id and self.company_id != website.company_id:
            return False
        return (self.active and self.website_id.id == website.id) or (
            not self.website_id and (self.selectable or self.sudo().code)
        )

    def _is_available_in_country(self, country_code):
        self.check_singleton()
        if not country_code or not self.country_group_ids:
            return True
        return country_code in self.country_group_ids.country_ids.mapped("code")

    def _get_domain_website_pricelists(self, website):
        return [
            ("active", "=", True),
            ("company_id", "in", [False, website.company_id.id]),
            "|",
            ("website_id", "=", website.id),
            "&",
            ("website_id", "=", False),
            "|",
            ("selectable", "=", True),
            ("code", "!=", False),
        ]
