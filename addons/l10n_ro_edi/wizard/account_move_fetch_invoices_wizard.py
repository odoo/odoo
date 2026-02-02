from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10n_ro_AccountMoveFetchInvoicesWizard(models.TransientModel):
    _name = 'l10n_ro_edi.account_move_fetch_invoices.wizard'
    _description = "Wizard to select date to fetch the invoices from"

    start_date = fields.Date(
        string="Synchronize from",
        help="Date from which you want to synchronize (back up to 60 days)",
        default=fields.Date.context_today,
        required=True,
    )
    # Technical field
    nb_days = fields.Integer(compute='_compute_nb_days')

    def action_l10n_ro_edi_fetch_invoices_from_date(self):
        self.env['account.move']._l10n_ro_edi_fetch_invoices(self.nb_days)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.depends('start_date')
    def _compute_nb_days(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            wizard.nb_days = (today - wizard.start_date).days + 1

    @api.constrains('start_date')
    def _check_start_date(self):
        for wizard in self:
            if not 0 < wizard.nb_days <= 60:
                raise ValidationError(_("You cannot synchronize invoices that are older than 60 days"))
