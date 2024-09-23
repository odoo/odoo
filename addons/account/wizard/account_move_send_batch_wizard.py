from odoo import _, api, Command, fields, models


class AccountMoveSendBatchWizard(models.TransientModel):
    """Wizard that handles the sending of multiple invoices."""
    _name = 'account.move.send.batch.wizard'
    _inherit = ['account.move.send']
    _description = "Account Move Send Batch Wizard"

    move_ids = fields.Many2many(comodel_name='account.move', required=True)
    summary_data = fields.Json(compute='_compute_summary_data')
    alerts = fields.Json(compute='_compute_alerts')

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)
        if 'move_ids' in fields_list and 'move_ids' not in results:
            move_ids = self._context.get('active_ids', [])
            results['move_ids'] = [Command.set(move_ids)]
        return results

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_summary_data(self):
        sending_methods = dict(self.env['res.partner']._fields['invoice_sending_method'].selection)
        for wizard in self:
            wizard.summary_data = {
                sending_method: {'count': len(moves), 'label': sending_methods[sending_method]}
                for sending_method, moves in wizard.move_ids.grouped(self._get_default_sending_method).items()
            }

    @api.depends('summary_data')
    def _compute_alerts(self):
        for wizard in self:
            moves_data = {
                move: {
                    'sending_methods': {self._get_default_sending_method(move)},
                    'invoice_edi_format': self._get_default_invoice_edi_format(move),
                    'extra_edis': self._get_default_extra_edis(move),
                }
                for move in wizard.move_ids
            }
            wizard.alerts = self._get_alerts(wizard.move_ids, moves_data)

    # -------------------------------------------------------------------------
    # CONSTRAINS
    # -------------------------------------------------------------------------

    @api.constrains('move_ids')
    def _check_move_ids_constrains(self):
        for wizard in self:
            self._check_move_constrains(wizard.move_ids)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        """ Launch asynchronously the generation and sending of invoices."""
        self.ensure_one()
        if self.alerts:
            self._raise_danger_alerts(self.alerts)
        if force_synchronous:
            self.env['account.move.send']._generate_and_send_invoices(self.move_ids, allow_fallback_pdf=allow_fallback_pdf)
            return

        self.move_ids.sending_data = {
            'author_user_id': self.env.user.id,
            'author_partner_id': self.env.user.partner_id.id,
        }
        self.env.ref('account.ir_cron_account_move_send')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _('Sending invoices'),
                'message': _('Invoices are being sent in the background.'),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
