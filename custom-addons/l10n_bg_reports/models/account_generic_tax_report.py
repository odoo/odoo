# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, models, _
from odoo.tools import float_is_zero


class BulgarianTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_bg.tax.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Bulgarian Tax Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings):
        # Overridden to prevent having unnecessary lines from the generic tax report.
        return []

    def _generate_tax_closing_entries(self, report, options, closing_moves=None, companies=None):
        def _get_external_value(xml_id):
            return self.env['account.report.external.value'].search([
                ('target_report_expression_id', '=', self.env.ref(xml_id).id),
                ('date', '>=', options['date']['date_from']),
                ('date', '<=', options['date']['date_to']),
            ])

        external_values = {
            'line_80': _get_external_value('l10n_bg.l10n_bg_tax_report_80_tag'),
            'line_81': _get_external_value('l10n_bg.l10n_bg_tax_report_81_tag'),
            'line_82': _get_external_value('l10n_bg.l10n_bg_tax_report_82_tag'),
        }

        closing_moves = super()._generate_tax_closing_entries(report, options, closing_moves, companies)

        vat_to_refund = external_values['line_80'].value + external_values['line_81'].value + external_values['line_82'].value

        # User requested a vat refund.
        if not float_is_zero(vat_to_refund, precision_rounding=closing_moves.currency_id.rounding):
            # Since we only override the closing moves when we have external values and external values are not
            # available on multi-company, we will always get exactly one closing move.
            for closing_move in closing_moves:
                account_vat_to_recover = self.env['account.account'].search([
                    ('code', '=like', '4538%'),
                    ('company_id', '=', closing_move.company_id.id)
                ], limit=1)

                account_vat_to_pay = self.env['account.account'].search([
                    ('code', '=like', '4539%'),
                    ('company_id', '=', closing_move.company_id.id)
                ], limit=1)

                vat_to_recover = account_vat_to_recover.current_balance

                # The tax report has an error when the user is asking for a refund when there is nothing to be refunded
                # or when the user didn't request the exact recoverable amount.
                has_error = closing_move.currency_id.is_zero(vat_to_recover) or closing_move.currency_id.compare_amounts(vat_to_recover, vat_to_refund)
                receivable_account = account_vat_to_pay if closing_move.currency_id.is_zero(vat_to_recover) else account_vat_to_recover

                closing_move.write({
                    'tax_report_control_error': has_error,
                    'line_ids': [
                        Command.create({
                            'name': _('Receivables tax amount'),
                            'account_id': receivable_account.id,
                            'credit': vat_to_refund,
                        }),
                        Command.create({
                            'name': _('Outstanding vat refund'),
                            'account_id': closing_move.company_id.account_journal_payment_debit_account_id.id,
                            'debit': vat_to_refund,
                        }),
                    ]
                })

        return closing_moves
