from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id'])
    l10n_pt_pos_at_series_id = fields.Many2one(
        'l10n_pt.at.series',
        string="Official Series of the Tax Authority",
        copy=False,
    )
    l10n_pt_pos_at_series_line_id = fields.Many2one(
        'l10n_pt.at.series.line',
        string="Document-specific AT Series",
        compute="_compute_l10n_pt_pos_at_series_line_id",
    )

    _sql_constraints = [
        (
            'unique_l10n_pt_pos_at_series_id',
            'unique(l10n_pt_pos_at_series_id)',
            'An AT series can only be assigned to one POS configuration.'
        )
    ]

    def _l10n_pt_pos_verify_config(self):
        if not self.l10n_pt_pos_at_series_id or self.l10n_pt_pos_at_series_line_id.type != 'pos_order':
            raise RedirectWarning(
                _('You have to set an Official Series of type Invoice/Receipt (FR) for this POS configuration.'),
                {
                    "view_mode": "form",
                    "res_model": "pos.config",
                    "type": "ir.actions.act_window",
                    "res_id": self.id,
                    "views": [[self.env.ref("l10n_pt_pos.pos_config_view_form_inherit_pt").id, "form"]],
                },
                _("Go to the POS configuration")
            )

        if incorrect_products := self.env['product.product'].search([
            ('available_in_pos', '=', True),
            ('combo_ids', '=', False),
        ]).filtered(lambda p: not p.default_code or not p.taxes_id):
            raise RedirectWarning(
                _("All products should have one tax and an internal reference."),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Incorrect products',
                    'res_model': 'product.product',
                    'view_mode': 'list',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', incorrect_products.ids)],
                },
                _("Incorrect products")
            )

        payment_methods = self.env['pos.payment.method'].search([('config_ids', 'in', self.ids)])
        missing_payment_mechanism = payment_methods.filtered(lambda pm: not pm.l10n_pt_pos_payment_mechanism)
        missing_at_series = payment_methods.filtered(
            lambda pm: pm.journal_id.type == 'bank'
            and not pm.l10n_pt_pos_default_at_series_id
        )
        msg = ""
        if missing_payment_mechanism:
            msg += _("All payment methods available for this Point of Sale should have a payment mechanism. ")
        if missing_at_series:
            msg += _("Payment methods with a bank journal require a default AT Series.")
        if msg:
            raise RedirectWarning(
                msg,
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Payment Methods',
                    'res_model': 'pos.payment.method',
                    'view_mode': 'list',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', (missing_at_series + missing_payment_mechanism).ids)],
                },
                _("See Payment Methods"),
            )

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id or config.country_code != 'PT':
                continue
            config._l10n_pt_pos_verify_config()
        return super().open_ui()

    def write(self, vals):
        for config in self:
            if 'l10n_pt_pos_at_series_id' in vals and config.has_active_session:
                raise UserError(_("You cannot change the AT series of a Point of Sale with an open session. "
                                  "Try again once the session is closed."))
        return super().write(vals)

    @api.constrains('l10n_pt_pos_at_series_id')
    def _check_l10n_pt_pos_at_series_id(self):
        for config in self.filtered(lambda c: c.country_code == 'PT'):
            if (
                config.l10n_pt_pos_at_series_id
                and not config.l10n_pt_pos_at_series_id.at_series_line_ids.filtered(lambda line: line.type == 'pos_order')
            ):
                action_error = {
                    'view_mode': 'form',
                    'name': _('AT Series'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': config.l10n_pt_pos_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("There is no AT series of type 'Invoice/Receipt (FR)' for this POS Configuration registered under the series name %(series_name)s. Create a new series or view existing series via the Accounting Settings.",
                      series_name=config.l10n_pt_pos_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )

    @api.depends('l10n_pt_pos_at_series_id')
    def _compute_l10n_pt_pos_at_series_line_id(self):
        for at_series, orders in self.grouped('l10n_pt_pos_at_series_id').items():
            orders.l10n_pt_pos_at_series_line_id = at_series._get_line_for_type('pos_order') if at_series else None
