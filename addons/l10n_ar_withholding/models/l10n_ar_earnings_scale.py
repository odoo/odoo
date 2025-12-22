from odoo import models, fields, api


class L10nArEarningsScale(models.Model):
    _name = 'l10n_ar.earnings.scale'
    _description = 'l10n_ar.earnings.scale'

    name = fields.Char(required=True, translate=True)
    line_ids = fields.One2many('l10n_ar.earnings.scale.line', 'scale_id')


class L10nArEarningsScaleLine(models.Model):
    _name = 'l10n_ar.earnings.scale.line'
    _description = 'l10n_ar.earnings.scale.line'
    _order = 'to_amount'

    scale_id = fields.Many2one(
        'l10n_ar.earnings.scale', required=True, ondelete='cascade',
        help="Calculation of the withholding amount: From the taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum) subtract the immediately previous amount of the column 'S/ Exceeding $' to detect which row to work with and apply the percentage of said row to the result of the subtraction. Then add to this amount the amount of the '$' column."
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.ref('base.ARS'), store=False
    )
    from_amount = fields.Monetary(
        string='From $',
        currency_field='currency_id',
        compute="_compute_from_amount"
    )
    to_amount = fields.Monetary(
        string='To $',
        currency_field='currency_id',
        help="The taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum) must be between the amount in the 'S/ Exced' column. of $' and the amount of this column."
    )
    fixed_amount = fields.Monetary(
        string='$',
        currency_field='currency_id',
        help="To obtain the withholding amount first from the taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum) subtract the immediately previous amount of 'S/ Exced. of $' column to detect which row to work with and apply the percentage of said row to the result of the subtraction. Then add the amount of this column to the result of applying the percentage."
    )
    percentage = fields.Monetary(
        string='Add %',
        currency_field='currency_id',
        help="Percentage to apply to the result of the subtraction between the taxable amount (tax base + tax basis of the previous month - non-taxable minimum) and the immediately previous amount of 'S/ Exced. from $' column."
    )
    excess_amount = fields.Monetary(
        string='S/ Exceeding $',
        currency_field='currency_id',
        help="From the taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum) subtract the immediately previous amount of this column to detect which row to work with and apply the percentage of said row to the result of the subtraction."
    )

    @api.depends('to_amount', 'scale_id.line_ids')
    def _compute_from_amount(self):
        for line in self:
            line.from_amount = line.scale_id.line_ids.sorted(reverse=True).filtered(lambda l: l.to_amount < line.to_amount)[:1].to_amount
