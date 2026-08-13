from odoo import Command, models, fields, api, _
from odoo.addons.account.models.exceptions import TaxClosingNonPostedDependingMovesError
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    move_ids = fields.Many2many('account.move')
    force_post = fields.Boolean(string="Force", help="Entries in the future are set to be auto-posted by default. Check this checkbox to post them now.")
    display_force_post = fields.Boolean(compute='_compute_display_force_post')
    is_entries = fields.Boolean(compute='_compute_is_entries')
    abnormal_date_partner_ids = fields.One2many('res.partner', compute='_compute_abnormal_date_partner_ids')
    ignore_abnormal_date = fields.Boolean()
    abnormal_amount_partner_ids = fields.One2many('res.partner', compute='_compute_abnormal_amount_partner_ids')
    ignore_abnormal_amount = fields.Boolean()

    @api.depends('move_ids')
    def _compute_display_force_post(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            wizard.display_force_post = wizard.move_ids.filtered(lambda m: (m.date or m.invoice_date or today) > today)

    @api.depends('move_ids')
    def _compute_is_entries(self):
        for wizard in self:
            wizard.is_entries = all(move_type == 'entry' for move_type in wizard.move_ids.mapped('move_type'))

    @api.depends('move_ids')
    def _compute_abnormal_date_partner_ids(self):
        for wizard in self:
            wizard.abnormal_date_partner_ids = wizard.move_ids.filtered('abnormal_date_warning').partner_id

    @api.depends('move_ids')
    def _compute_abnormal_amount_partner_ids(self):
        for wizard in self:
            wizard.abnormal_amount_partner_ids = wizard.move_ids.filtered('abnormal_amount_warning').partner_id

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if 'move_ids' in fields_list and not result.get('move_ids'):
            if self._context.get('active_model') == 'account.move':
                domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
            elif self._context.get('active_model') == 'account.journal':
                domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
            else:
                raise UserError(_("Missing 'active_model' in context."))

            moves = self.env['account.move'].search(domain).filtered('line_ids')
            if not moves:
                raise UserError(_('There are no journal items in the draft state to post.'))
            result['move_ids'] = [Command.set(moves.ids)]

        return result

    def validate_move(self):
        if self.ignore_abnormal_amount:
            self.abnormal_amount_partner_ids.ignore_abnormal_invoice_amount = True
        if self.ignore_abnormal_date:
            self.abnormal_date_partner_ids.ignore_abnormal_invoice_date = True
        if self.force_post:
            self.move_ids.auto_post = 'no'
        try:
            self.move_ids._post(not self.force_post)
        except TaxClosingNonPostedDependingMovesError as exception:
            return {
                "type": "ir.actions.client",
                "tag": "account_reports.redirect_action",
                "target": "new",
                "name": "Depending Action",
                "params": {
                    "depending_action": exception.args[0],
                    "message": _("It seems there is some depending closing move to be posted"),
                    "button_text": _("Depending moves"),
                },
                'context': {
                    'dialog_size': 'medium',
                },
            }
        if autopost_bills_wizard := self.move_ids._show_autopost_bills_wizard():
            return autopost_bills_wizard
        return {'type': 'ir.actions.act_window_close'}
