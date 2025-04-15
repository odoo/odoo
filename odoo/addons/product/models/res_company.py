# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._activate_or_create_pricelists()
        return companies

    def _activate_or_create_pricelists(self):
        """ Manage the default pricelists for needed companies. """
        if self.env.context.get('disable_company_pricelist_creation'):
            return

        if self.user_has_groups('product.group_product_pricelist'):
            companies = self or self.env['res.company'].search([])
            ProductPricelist = self.env['product.pricelist'].sudo()
            # Activate existing default pricelists
            default_pricelists_sudo = ProductPricelist.with_context(active_test=False).search(
                [('item_ids', '=', False), ('company_id', 'in', companies.ids)]
            ).filtered(lambda pl: pl.currency_id == pl.company_id.currency_id)
            default_pricelists_sudo.action_unarchive()
            companies_without_pricelist = companies.filtered(
                lambda c: c.id not in default_pricelists_sudo.company_id.ids
            )
            # Create missing default pricelists
            ProductPricelist.create([
                company._get_default_pricelist_vals() for company in companies_without_pricelist
            ])

    def _get_default_pricelist_vals(self):
        """Add values to the default pricelist at company creation or activation of the pricelist

        Note: self.ensure_one()

        :rtype: dict
        """
        self.ensure_one()
        values = {}
        values.update({
            'name': _("Default %s pricelist", self.currency_id.name),
            'currency_id': self.currency_id.id,
            'company_id': self.id,
            'sequence': 10,
        })
        return values

    def write(self, vals):
        """Delay the automatic creation of pricelists post-company update.

        This makes sure that the pricelist(s) automatically created are created with the right
        currency.
        """
        if not vals.get('currency_id'):
            return super().write(vals)

        enabled_pricelists = self.user_has_groups('product.group_product_pricelist')
        res = super(
            ResCompany, self.with_context(disable_company_pricelist_creation=True)
        ).write(vals)
        if not enabled_pricelists and self.user_has_groups('product.group_product_pricelist'):
            self.browse()._activate_or_create_pricelists()

        return res
