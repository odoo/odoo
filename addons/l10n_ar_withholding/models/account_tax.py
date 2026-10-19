from odoo import api, fields, models
from odoo.exceptions import ValidationError

EARNINGS_TAX_TYPES = ('earnings', 'earnings_scale')


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ar_withholding_tax_type = fields.Selection(
        string='Argentine Withhold type',
        selection=[
            ('earnings', 'Earnings'),
            ('earnings_scale', 'Earnings Scale'),
            ('iibb_untaxed', 'IIBB Untaxed'),
            ('iibb_total', 'IIBB Total Amount'),
        ],
        tracking=True,
    )
    l10n_ar_code = fields.Char('ARCA Code', tracking=True)
    l10n_ar_non_taxable_amount = fields.Float(
        string='Non Taxable Amount',
        digits='Account',
        tracking=True,
        help="Until this base amount, the tax is not applied.",
    )
    l10n_ar_minimum_threshold = fields.Float(
        string="Minimum Threshold",
        tracking=True,
        help="If the calculated withholding tax amount is lower than minimum withholding threshold then it is 0.0.")
    l10n_ar_state_id = fields.Many2one(
        comodel_name='res.country.state',
        string="Jurisdiction",
        ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
        tracking=True,
    )
    l10n_ar_scale_id = fields.Many2one(
        comodel_name='l10n_ar.earnings.scale',
        string="Scale",
        tracking=True,
        help="Earnings table scale if tax type is 'Earnings Scale'.",
    )

    @api.constrains('is_withholding_tax', 'l10n_ar_withholding_tax_type', 'l10n_ar_scale_id')
    def _check_l10n_ar_withholding_tax_type_alignment(self):
        for tax in self.filtered(lambda t: t.country_code == 'AR'):
            if tax.l10n_ar_withholding_tax_type and not tax.is_withholding_tax:
                raise ValidationError(self.env._("A tax cannot have an Argentine Withhold Type if it is not a withholding tax. Please, check the Withhold checkbox."))
            if tax.l10n_ar_withholding_tax_type == 'earnings_scale' and not tax.l10n_ar_scale_id:
                raise ValidationError(self.env._(
                    "The tax %(tax_name)s withholds according to an earnings scale, please set the scale it uses.",
                    tax_name=tax.display_name,
                ))
            if tax.l10n_ar_withholding_tax_type in ('earnings', 'earnings_scale') and tax.type_tax_use == 'purchase' and not tax.l10n_ar_code:
                raise ValidationError(self.env._("The earnings tax type must have an ARCA Code."))

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._l10n_ar_clean_regime_vals(vals) for vals in vals_list])

    def write(self, vals):
        return super().write(self._l10n_ar_clean_regime_vals(vals))

    @api.model
    def _l10n_ar_clean_regime_vals(self, vals):
        """ Some value are hidden in the form but still there in the value,
        clean the dangerous ones. Note we don't handle this with an onchange to
        avoid resetting the view when the user modifies a checkbox for testing/by mistake.
        """
        vals = dict(vals)
        if not vals.get('is_withholding_tax', True):
            vals['l10n_ar_withholding_tax_type'] = False
        earnings_regime = vals.get('l10n_ar_withholding_tax_type', 'earnings') in EARNINGS_TAX_TYPES
        if not earnings_regime or vals.get('type_tax_use', 'purchase') != 'purchase':
            vals['l10n_ar_code'] = False  # only an earnings regime withheld on the purchase side has one
        return vals

    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        """ Override to keep withholding lines with a 0% tax.
        These lines are important for the Argentinian localization and as the withholding table is not editable,
        if they are removed, then there's no way to re-add them afterwards.
        """
        res = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        record = base_line['record']
        if isinstance(record, models.Model) and record._name == "account.move.line":
            if any(tax.country_code == 'AR' and tax.is_withholding_tax for tax in record.tax_ids):
                res["__keep_zero_line"] = True
        return res
