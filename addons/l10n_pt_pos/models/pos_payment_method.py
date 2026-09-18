from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning

from odoo.addons.l10n_pt_certification.models.account_payment_method import L10N_PT_PAYMENT_MECHANISMS


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    l10n_pt_pos_payment_mechanism = fields.Selection(
        selection=L10N_PT_PAYMENT_MECHANISMS,
        string='Payment Mechanism',
        compute='_compute_l10n_pt_pos_payment_mechanism',
        store=True,
        readonly=False,
        help="This payment method's mechanism according to Portuguese requirements.",
    )
    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_pos_default_at_series_id = fields.Many2one(
        'l10n_pt.at.series',
        string="Default AT Series (POS)",
        help="The default AT series used in combined payments created for a POS Session",
        compute='_compute_l10n_pt_pos_default_at_series_id',
        store=True,
        readonly=False,
    )

    @api.depends('is_cash_count', 'country_code')
    def _compute_l10n_pt_pos_payment_mechanism(self):
        # Default payment mechanism for cash to 'NU' (Numerário = Cash)
        for payment_method in self:
            if payment_method.is_cash_count and payment_method.country_code == 'PT':
                payment_method.l10n_pt_pos_payment_mechanism = 'NU'
            else:
                payment_method.l10n_pt_pos_payment_mechanism = None

    @api.depends('journal_id', 'company_id')
    def _compute_l10n_pt_pos_default_at_series_id(self):
        payment_methods = self.filtered(
            lambda pm: not (
                    pm.l10n_pt_pos_default_at_series_id
                    and pm.l10n_pt_pos_default_at_series_id.payment_journal_id == pm.journal_id
                    and pm.l10n_pt_pos_default_at_series_id.at_series_active
            ))

        for (company, journal), grouped_payment_methods in payment_methods.grouped(lambda pm: (pm.company_id, pm.journal_id)).items():
            if company and journal:
                # Get the possible AT series for each group of payment methods from same company and journal
                at_series = self.env['l10n_pt.at.series'].search([
                    '|',
                    '&',
                    ('company_id', '=', company.id),
                    ('company_exclusive_series', '=', True),
                    '&',
                    ('company_id', 'in', company.parent_ids.ids),
                    ('company_exclusive_series', '=', False),
                    ('active', '=', True),
                    ('payment_journal_id', '=', journal.id),
                ], limit=1)
                grouped_payment_methods.l10n_pt_pos_default_at_series_id = at_series
            else:
                grouped_payment_methods.l10n_pt_pos_default_at_series_id = None

    @api.constrains('l10n_pt_pos_default_at_series_id')
    def _check_l10n_pt_pos_default_at_series_id(self):
        # If there are no AT Series lines of type Payment Receipt, request user to add one
        for payment_method in self.filtered(lambda c: c.company_id.country_id.code == 'PT'):
            if (
                payment_method.l10n_pt_pos_default_at_series_id
                and not payment_method.l10n_pt_pos_default_at_series_id.at_series_line_ids.filtered(lambda line: line.type == 'payment_receipt')
            ):
                action_error = {
                    'view_mode': 'form',
                    'name': _('AT Series'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': payment_method.l10n_pt_pos_default_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("There is no AT series of type 'Payment Receipt (RG)' registered under the series name %(series_name)s. "
                      "Create a new series or view existing series via the Accounting Settings.",
                      series_name=payment_method.l10n_pt_pos_default_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )
