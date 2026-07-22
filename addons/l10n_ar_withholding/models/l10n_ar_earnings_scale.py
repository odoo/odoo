from odoo import models, fields


class L10n_ArEarningsScale(models.Model):
    _name = 'l10n_ar.earnings.scale'
    _description = 'l10n_ar.earnings.scale'

    name = fields.Char(required=True, translate=True)
    line_ids = fields.One2many('l10n_ar.earnings.scale.line', 'scale_id')

    def _l10n_ar_get_tax_amount_from_bracket(self, net_amount):
        """ Return the withholding given by the progressive brackets of the scale, which replaces
        the rate of the taxes using it.
        The top of an ARCA table reads "de $X en adelante": a base above the last bracket is withheld
        at that bracket rather than escaping the scale.
        """
        self.ensure_one()
        bracket = self.line_ids.filtered(lambda line: line.from_amount <= net_amount < line.to_amount)[:1]
        if not bracket:
            highest_bracket = self.line_ids.sorted('to_amount')[-1:]
            if net_amount >= highest_bracket.to_amount:
                bracket = highest_bracket
        if not bracket:
            # Below the table: there is nothing to withhold yet.
            return 0.0
        return (net_amount - bracket.from_amount) * bracket.percentage / 100 + bracket.fixed_amount
