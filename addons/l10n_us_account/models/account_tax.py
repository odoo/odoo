# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_us_jurisdiction_type = fields.Selection(
        selection=[
            ('state', 'State'),
            ('county', 'County'),
            ('city', 'City'),
            ('special', 'Special'),
        ],
        string="Jurisdiction Type",
        copy=False,
    )
    l10n_us_state_id = fields.Many2one(
        comodel_name='res.country.state',
        string="State",
        copy=False,
        domain="[('country_id.code', '=', 'US')]",
    )
    l10n_us_county_id = fields.Many2one(
        comodel_name='l10n_us.res.county',
        string="County",
        copy=False,
        domain="[('state_id', '=', l10n_us_state_id)]",
    )
    l10n_us_city_id = fields.Many2one(
        comodel_name='res.city',
        string="City",
        copy=False,
        domain="[('state_id', '=', l10n_us_state_id)]",
    )
    l10n_us_exempt_tax_ids = fields.One2many(
        comodel_name='account.tax',
        inverse_name='l10n_us_exempt_parent_tax_id',
        string="Exempt Tax",
    )
    l10n_us_nontaxable_tax_ids = fields.One2many(
        comodel_name='account.tax',
        inverse_name='l10n_us_nontaxable_parent_tax_id',
        string="Nontaxable Tax",
    )
    l10n_us_exempt_parent_tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        string="Exempt For",
        ondelete='set null',
        index='btree_not_null',
    )
    l10n_us_nontaxable_parent_tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        string="Nontaxable For",
        ondelete='set null',
        index='btree_not_null',
    )

    @api.onchange('l10n_us_jurisdiction_type', 'l10n_us_state_id')
    def _onchange_l10n_us_jurisdiction(self):
        if not self.l10n_us_jurisdiction_type:
            self.l10n_us_state_id = False
        if self.l10n_us_jurisdiction_type != 'county' or self.l10n_us_county_id.state_id != self.l10n_us_state_id:
            self.l10n_us_county_id = False
        if self.l10n_us_jurisdiction_type != 'city' or self.l10n_us_city_id.state_id != self.l10n_us_state_id:
            self.l10n_us_city_id = False

    @api.constrains(
        'l10n_us_exempt_parent_tax_id', 'l10n_us_nontaxable_parent_tax_id',
        'l10n_us_exempt_tax_ids', 'l10n_us_nontaxable_tax_ids',
    )
    def _check_l10n_us_parent_tax_id(self):
        for tax in self:
            parent = tax.l10n_us_exempt_parent_tax_id | tax.l10n_us_nontaxable_parent_tax_id
            if tax in parent:
                raise ValidationError(_("A tax cannot be its own exempt or nontaxable tax."))
            if parent and (
                tax.l10n_us_exempt_tax_ids
                or tax.l10n_us_nontaxable_tax_ids
                or parent.l10n_us_exempt_parent_tax_id
                or parent.l10n_us_nontaxable_parent_tax_id
            ):
                raise ValidationError(_("An exempt or nontaxable tax cannot have exempt or nontaxable taxes of its own."))

    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        # Override. Keep $0 tax lines to report exempt/nontaxable for US tax report
        res = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        tax = tax_data['tax']
        if tax.country_id.code == 'US' and (
            tax.l10n_us_jurisdiction_type
            or tax.l10n_us_exempt_parent_tax_id
            or tax.l10n_us_nontaxable_parent_tax_id
        ):
            res["__keep_zero_line"] = True
        return res
