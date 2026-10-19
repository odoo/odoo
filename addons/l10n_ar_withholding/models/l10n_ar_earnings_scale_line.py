from odoo import models, fields, api


class L10n_ArEarningsScaleLine(models.Model):
    _name = 'l10n_ar.earnings.scale.line'
    _description = 'l10n_ar.earnings.scale.line'
    _order = 'to_amount'

    scale_id = fields.Many2one(
        comodel_name='l10n_ar.earnings.scale',
        required=True,
        ondelete='cascade',
        help="Calculation of the withholding amount: from the taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum), find the bracket it falls in, apply the percentage of that bracket to what exceeds its 'From $' and add the amount of its '$' column."
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        default=lambda self: self.env.ref('base.ARS'),
        store=False,
    )
    from_amount = fields.Monetary(
        string='From $',
        compute="_compute_from_amount"
    )
    to_amount = fields.Monetary(
        string='To $',
        help="The taxable amount (tax base + tax bases applied this month to same tax and partner - non-taxable minimum) must be between the amount of the 'From $' column and the amount of this column."
    )
    fixed_amount = fields.Monetary(
        string='$',
        compute="_compute_fixed_amount",
        help="What the brackets below this one withhold in full, to be added to the percentage this bracket applies to what exceeds its 'From $'."
    )
    percentage = fields.Float(
        string='Add %',
        help="Percentage to apply to the part of the taxable amount (tax base + tax basis of the previous month - non-taxable minimum) that exceeds the 'From $' of this bracket."
    )

    @api.depends('to_amount', 'scale_id.line_ids.to_amount')
    def _compute_from_amount(self):
        for line in self:
            # A bracket starts where the previous one ends
            lower_brackets = line.scale_id.line_ids.filtered(lambda l: l.to_amount < line.to_amount)
            line.from_amount = max(lower_brackets.mapped('to_amount'), default=0.0)

    @api.depends('to_amount', 'scale_id.line_ids.to_amount', 'scale_id.line_ids.from_amount', 'scale_id.line_ids.percentage')
    def _compute_fixed_amount(self):
        for line in self:
            # ARCA publishes this column, but it only accumulates what the previous brackets withhold
            lower_brackets = line.scale_id.line_ids.filtered(lambda l: l.to_amount < line.to_amount)
            line.fixed_amount = sum(
                (bracket.to_amount - bracket.from_amount) * bracket.percentage / 100
                for bracket in lower_brackets
            )
