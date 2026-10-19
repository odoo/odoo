from collections import defaultdict
from odoo import _, api, Command, fields, models
from odoo.exceptions import RedirectWarning, UserError


class AccountMoveSendBatchWizard(models.TransientModel):
    """Wizard that handles the sending of multiple invoices."""
    _name = 'account.move.send.batch.wizard'
    _inherit = ['account.move.send']
    _description = "Send Invoice Batch Wizard"

    move_ids = fields.Many2many(comodel_name='account.move', required=True)
    summary_data = fields.Json(compute='_compute_summary_data')
    alerts = fields.Json(compute='_compute_alerts')

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields):
        # EXTENDS 'base'
        results = super().default_get(fields)
        if 'move_ids' in fields and 'move_ids' not in results:
            move_ids = self.env.context.get('active_ids', [])
            results['move_ids'] = [Command.set(move_ids)]
        return results

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_summary_data(self):
        extra_edis = self._get_all_extra_edis()
        sending_methods = dict(self.env['res.partner']._fields['invoice_sending_method']._description_selection(self.env))
        sending_methods['manual'] = _('Manually')  # in batch sending, everything is done asynchronously, we never "Download"

        for wizard in self:
            moves = wizard.move_ids._origin
            summary_data = defaultdict(lambda: {'count': 0, 'label': '', 'moves': []})

            if not moves:
                wizard.summary_data = summary_data
                continue

            for move in moves:
                move_info = {
                    'id': move.id,
                    'name': move.name or _("Draft"),
                    'partner_name': move.partner_id.name or _("No Partner"),
                }

                for edi in self._get_default_extra_edis(move):
                    summary_data[edi]['count'] += 1
                    summary_data[edi]['moves'].append(move_info)
                    if not summary_data[edi]['label']:
                        summary_data[edi]['label'] = _("by %s", extra_edis[edi]['label'])

                sending_methods_for_move = self._get_default_sending_methods(move)
                lightweight_settings = {
                    'sending_methods': sending_methods_for_move,
                    'extra_edis': self._get_default_extra_edis(move),
                    'invoice_edi_format': self._get_default_invoice_edi_format(move, sending_methods=sending_methods_for_move),
                }
                if 'email' in sending_methods_for_move:
                    lightweight_settings['mail_partner_ids'] = move.partner_id.ids if move.partner_id.email else []

                for sending_method in sending_methods_for_move:
                    if self._is_applicable_to_move(sending_method, move, **lightweight_settings):
                        summary_data[sending_method]['count'] += 1
                        summary_data[sending_method]['moves'].append(move_info)
                        if not summary_data[sending_method]['label']:
                            summary_data[sending_method]['label'] = sending_methods[sending_method]

            wizard.summary_data = summary_data

    @api.depends('summary_data')
    def _compute_alerts(self):

        for wizard in self:
            moves_data = {}
            for move in wizard.move_ids._origin:
                sending_methods_for_move = self._get_default_sending_methods(move)
                moves_data[move] = {
                    'sending_methods': sending_methods_for_move,
                    'extra_edis': self._get_default_extra_edis(move),
                    'invoice_edi_format': self._get_default_invoice_edi_format(move, sending_methods=sending_methods_for_move),
                }
            wizard.alerts = self._get_alerts(wizard.move_ids._origin, moves_data)

    # -------------------------------------------------------------------------
    # CONSTRAINS
    # -------------------------------------------------------------------------

    @api.constrains('move_ids')
    def _check_move_ids_constraints(self):
        for wizard in self:
            self._check_move_constraints(wizard.move_ids)

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

        account_move_send_cron = self.env.ref('account.ir_cron_account_move_send')
        if not account_move_send_cron.sudo().active:
            if self.env.user.has_group('base.group_system'):
                raise RedirectWarning(
                    _("Batch invoice sending is unavailable. Please, activate the cron to enable batch sending of invoices."),
                    {
                        'views': [(False, 'form')],
                        'res_model': 'ir.cron',
                        'type': 'ir.actions.act_window',
                        'res_id': account_move_send_cron.id,
                        'target': 'current',
                    },
                    _("Go to cron configuration"),
                )
            raise UserError(_("Batch invoice sending is unavailable. Please, contact your system administrator to activate the cron to enable batch sending of invoices."))

        self.move_ids.sending_data = {
            'author_user_id': self.env.user.id,
            'author_partner_id': self.env.user.partner_id.id,
        }
        account_move_send_cron._trigger()
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
