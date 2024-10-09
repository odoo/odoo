# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from odoo import _, api, models
from odoo.api import ValuesType


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> ResCompany:
        companies = super().create(vals_list)
        companies._activate_or_create_pricelists()
        return companies

    def _activate_or_create_pricelists(self) -> None:
        """ Manage the default pricelists for needed companies. """
        if self.env.context.get('disable_company_pricelist_creation'):
            return

        if not self.env.user.has_group('product.group_product_pricelist'):
            return

        companies = self or self.env['res.company'].search([])
        ProductPricelist = self.env['product.pricelist'].sudo()
        # Activate existing default pricelists
        default_pricelists_sudo = ProductPricelist.with_context(active_test=False).search(
            [('item_ids', '=', False), ('company_id', 'in', companies.ids)]
        ).filtered(lambda pl: pl.currency_id == pl.company_id.currency_id)
        default_pricelists_sudo.action_unarchive()

        # Create missing default pricelists
        ProductPricelist.create([
            company._get_default_pricelist_vals()
            for company in companies
            if company.id not in default_pricelists_sudo.company_id.ids
        ])

    def _get_default_pricelist_vals(self) -> ValuesType:
        """Add values to the default pricelist at company creation or activation of the pricelist

        Note: self.ensure_one()
        """
        self.ensure_one()
        return {
            'name': _("Default"),
            'currency_id': self.currency_id.id,
            'company_id': self.id,
            'sequence': 10,
        }

    def write(self, vals: ValuesType) -> int:
        """Delay the automatic creation of pricelists post-company update.

        This makes sure that the pricelist(s) automatically created are created with the right
        currency.
        """
        if 'currency_id' not in vals:
            return super().write(vals)

        res = super(ResCompany, self.with_context(disable_company_pricelist_creation=True)).write(vals)
        self._activate_or_create_pricelists()

        return res
