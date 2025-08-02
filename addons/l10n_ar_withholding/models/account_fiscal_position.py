from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ar_tax_ids = fields.One2many('account.fiscal.position.l10n_ar_tax', 'fiscal_position_id')

    def _l10n_ar_add_taxes(self, partner, company, date, tax_type):
        """
        This method determines applicable taxes for a partner by filtering and matching
        tax rules based on the provided tax type ('perception' or 'withholding'), date,
        and company. It also handles cases where taxes are missing for a tax group.

        Args:
            partner (res.partner): The partner for whom taxes are being determined.
            company (res.company): The company context for the tax determination.
            date (datetime.date): The date to evaluate applicable taxes.
            tax_type (str): The type of tax ('perception' or 'withholding').

        Returns:
            account.tax: A recordset of applicable taxes.
        """
        # TODO we should try to unify this method with _get_tax_domain, _compute_withholdings and _check_tax_group_overlap
        self.ensure_one()
        taxes = self.env['account.tax']
        for fp_tax in self.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == tax_type):
            domain = self.env['l10n_ar.partner.tax']._check_company_domain(company)
            domain += [('tax_id.tax_group_id', '=', fp_tax.default_tax_id.tax_group_id.id)]
            domain += [
                '|', ('from_date', '<=', date), ('from_date', '=', False),
                '|', ('to_date', '>=', date), ('to_date', '=', False),
            ]
            if tax_type == 'perception':
                partner_tax = partner.l10n_ar_partner_perception_ids.filtered_domain(domain).mapped('tax_id')
            elif tax_type == 'withholding':
                partner_tax = partner.l10n_ar_partner_tax_ids.filtered_domain(domain).mapped('tax_id')
            # Add taxes for tax groups that were not set on the partner
            if not partner_tax:
                partner_tax = fp_tax._get_missing_taxes(partner, date)
            if partner_tax.l10n_ar_tax_type not in ["earnings", "earnings_scale"] and partner_tax.amount == 0:
                # if the tax is non earnings and the amount is 0, then we skip it
                continue
            taxes |= partner_tax
        return taxes

    def _get_fpos_ranking_functions(self, partner):
        """
        Overrides the `_get_fpos_ranking_functions` method to include a custom ranking
        function for fiscal positions based on Argentine withholding taxes.

        If the context does not include 'l10n_ar_withholding' or the company's country
        is not Argentina (country code "AR"), the method falls back to the parent class
        implementation.

        When the context includes 'l10n_ar_withholding' and the company's country is
        Argentina, the method adds a ranking function that prioritizes fiscal positions
        containing taxes of type 'withholding' (`l10n_ar_tax_ids`).

        Args:
            partner (res.partner): The partner for whom the fiscal position ranking
                functions are being determined.
        """
        if not self._context.get('l10n_ar_withholding') or self.env.company.country_id.code != "AR":
            return super()._get_fpos_ranking_functions(partner)
        return [('l10n_ar_tax_ids', lambda fpos: (any(tax.tax_type == 'withholding' for tax in fpos.l10n_ar_tax_ids)))] + super()._get_fpos_ranking_functions(partner)

    def map_tax(self, taxes):
        """ For argentinean fiscal positions without tax mapping we add domestic taxes becasue taxes are always requried
        on argentinean invoices so there is no use case for not having them.
        The other alternative would be to add the new fiscal positions on every VAT tax but that would be a lot of work
        for the user.
        """
        if not self.tax_ids and self.l10n_ar_tax_ids:
            return self.company_id.domestic_fiscal_position_id.map_tax(taxes)
        return super().map_tax(taxes)
