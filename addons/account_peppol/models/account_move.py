# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='PEPPOL status',
        copy=False,
    )

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to PEPPOL"))
        self.peppol_move_state = False
        self.send_and_print_values = False

    @api.depends('state')
    def _compute_peppol_move_state(self):
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        for move in self:
            if all([
                move.company_id.account_peppol_proxy_state in can_send,
                move.commercial_partner_id.account_peppol_is_endpoint_valid,
                move.state == 'posted',
                move.is_sale_document(include_receipts=True),
                not move.peppol_move_state,
            ]):
                move.peppol_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and move.peppol_move_state not in ('processing', 'done')
            ):
                move.peppol_move_state = False
            else:
                move.peppol_move_state = move.peppol_move_state

    def _is_peppol_enabled_by_default(self):
        """ Tells if Peppol can be used by default on the move (the configuration is correct).
        This is mainly used in account.move.send to preset checkboxes in the wizard, and defines the
        behavior in automatic invoicing flows.
        """
        self.ensure_one()
        return self.peppol_move_state == 'ready'
