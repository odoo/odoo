# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    # ------------------
    # Fields declaration
    # ------------------

    limit_to_withholding_tax = fields.Boolean(
        string="Withholding Tax",
        default=False,
        tracking=True,
        help="If set, this model will only match against invoices containing withholding taxes.\nThis only works if the transaction amount exactly matches the expected amount (invoice amount minus withholding taxes).",
    )

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _get_invoice_matching_amls_result(self, st_line, partner, candidate_vals):
        # todo this is in enterprise... may need an enterprise module.
        # EXTEND in order to filter out candidates that are not from a withholding invoice when limit_to_withholding_tax is set
        if self.limit_to_withholding_tax:
            amls = candidate_vals['amls']
            st_line_currency = st_line.foreign_currency_id or st_line.currency_id
            st_line_amount = abs(st_line._prepare_move_line_default_vals()[1]['amount_currency'])
            sum_residual = 0.0
            for aml in amls:
                amounts = aml._get_withholding_amounts()
                # It would be useless to keep lines above the statement line amount, and it causes trouble with EPD
                if not amounts['withholding'] or sum_residual >= st_line_amount:
                    candidate_vals['amls'] -= aml
                else:
                    # We get the residual amount in st_line currency and sum it for later comparison.
                    residual = st_line._prepare_counterpart_amounts_using_st_line_rate(
                        aml.currency_id,
                        amounts['residual_net'],
                        amounts['residual_net_currency'],
                    )['amount_currency']
                    sum_residual += abs(residual)
            else:
                # If payment tolerance is disabled, we need to ignore non-perfect matches at this point.
                # If enabled, the check will be handled later on.
                if not self.allow_payment_tolerance:
                    if not st_line_currency.compare_amounts(st_line_amount, sum_residual) == 0:
                        candidate_vals['amls'] = None

            # Handle the case where we filter out everything.
            if not candidate_vals['amls']:
                return  # By returning None, we will simply continue the loop and try the next model.

        return super()._get_invoice_matching_amls_result(st_line, partner, candidate_vals)

    def _check_rule_propositions(self, st_line, amls_values_list):
        # EXTEND in order to "ignore" the withholding amount and allow write off of that amount.
        # We simply update amls_values_list and remove the withholding amount from the vals;
        # this will allow the payment tolerance to apply to the net amount
        if self.limit_to_withholding_tax:
            for i, aml_vals in enumerate(amls_values_list):
                amounts = aml_vals['aml']._get_withholding_amounts()
                aml_vals['amount_residual'] = amounts['residual_net']
                aml_vals['amount_residual_currency'] = amounts['residual_net_currency']

        res = super()._check_rule_propositions(st_line, amls_values_list)

        if self.limit_to_withholding_tax and 'rejected' not in res:
            # We may get a perfect match; for withholding we still want to generate the writeoff line!
            # This is because we perfectly matched on the amount excluding withholding.
            res.add('allow_write_off')

        return res

    @api.depends('limit_to_withholding_tax')
    def _compute_lines_are_applicable(self):
        # EXTEND in order to apply lines also when withholding tax is enabled on the model.
        super()._compute_lines_are_applicable()
        for model in self:
            model.lines_are_applicable = model.lines_are_applicable or model.limit_to_withholding_tax
