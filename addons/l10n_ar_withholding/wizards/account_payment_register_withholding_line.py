from odoo import api, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _inherit = 'account.payment.register.withholding.line'

    @api.depends('payment_register_id.withhold')
    def _compute_comodel_percentage_paid_factor(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        The generic withholding-only factor prorates on withholding taxes declared
        on the invoice lines, which Argentina doesn't set.
        """
        super()._compute_comodel_percentage_paid_factor()
        for wizard, lines in self.grouped('payment_register_id').items():
            if wizard.country_code != 'AR' or wizard.withhold != 'withhold':
                continue

            residual_amount = wizard._get_total_amounts_to_pay(wizard._get_batches())['full_amount']
            invoice_amount = wizard._get_total_amount_in_wizard_currency()
            lines.comodel_percentage_paid_factor = (
                abs(residual_amount / invoice_amount) if residual_amount and invoice_amount else 1.0
            )

    @api.depends('tax_id')
    def _compute_base_amount(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        Argentina does not only rely on the paid factor unlike generic module.
        The paid factor should be applied either the untaxed amount, or the full amount
        of the invoice being settled, depending on the nature of the tax.
        """
        ar_lines = self.filtered(lambda l: l.payment_register_id.country_code == 'AR' and l.tax_id)
        for line in ar_lines:
            levied_on = sum(
                move.currency_id._convert(
                    from_amount=move.amount_total if line.tax_id.l10n_ar_withholding_tax_type == 'iibb_total' else move.amount_untaxed,
                    to_currency=line.comodel_currency_id,
                    company=line.company_id,
                    date=line.comodel_date,
                )
                for move in line.payment_register_id.line_ids.move_id
            )
            line.base_amount = levied_on * line.comodel_percentage_paid_factor

        super(AccountPaymentRegisterWithholdingLine, self - ar_lines)._compute_base_amount()
