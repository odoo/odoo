# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"
    _clear_cache_name = "default"

    # === DEFAULT METHODS ===#

    def _default_website(self):
        """Find the first company's website, if there is one."""
        company_id = self.default_get(["company_id"]).get("company_id", self.env.company.id)
        return self.env["website"].search([("company_id", "=", company_id)], limit=1)

    # === FIELDS ===#

    website_id = fields.Many2one(
        string="Website",
        comodel_name="website",
        ondelete="restrict",
        default=_default_website,
        ui_domain="[('company_id', '=?', company_id)]",
        tracking=20,
        help="If you want a pricelist to be available on a website,"
        "you must fill in this field or make it selectable."
        "Otherwise, the pricelist will not apply to any website.",
    )
    code = fields.Char(string="Access Code", groups="base.group_user")
    selectable = fields.Boolean(help="Allow the end user to choose this price list")
    tax_display = fields.Selection(
        string="eCommerce Price Display",
        selection=[("tax_included", "Taxes Included"), ("tax_excluded", "Taxes Excluded")],
    )

    # === CONSTRAINT METHODS ===#

    @api.constrains("company_id", "website_id")
    def _check_websites_in_company(self):
        """Prevent misconfiguration multi-website/multi-companies.

        If the record has a company, the website should be from that company.
        """
        for record in self.filtered(lambda pl: pl.website_id and pl.company_id):
            if record.website_id.company_id != record.company_id:
                raise ValidationError(
                    record.env._(
                        "Only the company's websites are allowed."
                        "\nLeave the Company field empty or select a website from that company."
                    )
                )

    # === BUSINESS METHODS ===#

    def _get_partner_pricelist_multi_search_domain_hook(self, company_id):
        domain = super()._get_partner_pricelist_multi_search_domain_hook(company_id)
        if website := self.env.website:
            domain &= self._get_website_pricelists_domain(website)
        return domain

    def _get_partner_pricelist_multi_filter_hook(self):
        res = super()._get_partner_pricelist_multi_filter_hook()
        if website := self.env.website:
            res = res.filtered(lambda pl: pl._is_available_on_website(website))
        return res

    def _is_available_on_website(self, website) -> bool:
        self.ensure_one()
        return bool(self.sudo().filtered_domain(self._get_website_pricelists_domain(website)))

    def _is_available_in_country(self, country_code) -> bool:
        self.ensure_one()

        return (
            not country_code
            or not self.country_group_ids
            or country_code in self.country_group_ids.country_ids.mapped("code")
        )

    def _get_website_pricelists_domain(self, website) -> Domain:
        """To be able to be used on a website, a pricelist should either:
        - Have its `website_id` set to current website (specific pricelist).
        - Have no `website_id` set and should be `selectable` (generic pricelist)
          or should have a `code` (generic promotion).
        - Have no `company_id` or a `company_id` matching its website one.

        Note: A pricelist without a website_id, not selectable and without a
              code is a backend pricelist.
        """
        return Domain([
            ("active", "=", True),
            ("company_id", "in", [False, website.company_id.id]),
            "|",
            ("website_id", "=", website.id),
            "&",
            ("website_id", "=", False),
            "|",
            ("selectable", "=", True),
            ("code", "!=", False),
        ])
