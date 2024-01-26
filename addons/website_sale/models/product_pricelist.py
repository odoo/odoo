# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.website.models import ir_http


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    #=== DEFAULT METHODS ===#

    def _default_website(self):
        """ Find the first company's website, if there is one. """
        company_id = self.env.company.id

        if self._context.get('default_company_id'):
            company_id = self._context.get('default_company_id')

        domain = [('company_id', '=', company_id)]
        return self.env['website'].search(domain, limit=1)

    #=== FIELDS ===#

    website_id = fields.Many2one(
        string="Website",
        comodel_name='website',
        ondelete='restrict',
        default=_default_website,
        domain="[('company_id', '=?', company_id)]",
        tracking=20,
        help="If you want a pricelist to be available on a website,"
             "you must fill in this field or make it selectable."
             "Otherwise, the pricelist will not apply to any website."
    )
    code = fields.Char(string="E-commerce Promotional Code", groups='base.group_user')
    selectable = fields.Boolean(help="Allow the end user to choose this price list")

    #=== CONSTRAINT METHODS ===#

    @api.constrains('company_id', 'website_id')
    def _check_websites_in_company(self):
        """ Prevent misconfiguration multi-website/multi-companies.

        If the record has a company, the website should be from that company.
        """
        for record in self.filtered(lambda pl: pl.website_id and pl.company_id):
            if record.website_id.company_id != record.company_id:
                raise ValidationError(_(
                    "Only the company's websites are allowed."
                    "\nLeave the Company field empty or select a website from that company."
                ))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('company_id') and not vals.get('website_id'):
                # l10n modules install will change the company currency, creating a
                # pricelist for that currency. Do not use user's company in that
                # case as module install are done with OdooBot (company 1)
                # YTI FIXME: The fix is not at the correct place
                # It be set when we actually create the pricelist
                self = self.with_context(default_company_id=vals['company_id'])
        pricelists = super().create(vals_list)
        if pricelists:
            self.env.registry.clear_cache()
        return pricelists

    def write(self, data):
        res = super().write(data)
        self and self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self and self.env.registry.clear_cache()
        return res

    #=== BUSINESS METHODS ===#

    def _get_partner_pricelist_multi_search_domain_hook(self, company_id):
        domain = super()._get_partner_pricelist_multi_search_domain_hook(company_id)
        website = ir_http.get_request_website()
        if website:
            domain += self._get_website_pricelists_domain(website)
        return domain

    def _get_partner_pricelist_multi_filter_hook(self):
        res = super()._get_partner_pricelist_multi_filter_hook()
        website = ir_http.get_request_website()
        if website:
            res = res.filtered(lambda pl: pl._is_available_on_website(website))
        return res

    def _is_available_on_website(self, website):
        """ To be able to be used on a website, a pricelist should either:
        - Have its `website_id` set to current website (specific pricelist).
        - Have no `website_id` set and should be `selectable` (generic pricelist)
          or should have a `code` (generic promotion).
        - Have no `company_id` or a `company_id` matching its website one.

        Note: A pricelist without a website_id, not selectable and without a
              code is a backend pricelist.

        Change in this method should be reflected in `_get_website_pricelists_domain`.
        """
        self.ensure_one()
        if self.company_id and self.company_id != website.company_id:
            return False
        return self.active and self.website_id.id == website.id or (not self.website_id and (self.selectable or self.sudo().code))

    def _is_available_in_country(self, country_code):
        self.ensure_one()
        if not country_code or not self.country_group_ids:
            return True
        return country_code in self.country_group_ids.country_ids.mapped('code')

    def _get_website_pricelists_domain(self, website):
        ''' Check above `_is_available_on_website` for explanation.
        Change in this method should be reflected in `_is_available_on_website`.
        '''
        return [
            ('active', '=', True),
            ('company_id', 'in', [False, website.company_id.id]),
            '|', ('website_id', '=', website.id),
            '&', ('website_id', '=', False),
            '|', ('selectable', '=', True), ('code', '!=', False),
        ]
