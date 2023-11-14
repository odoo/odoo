# -*- coding:utf-8 -*-
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
            ('canceled', 'Canceled'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='PEPPOL status',
        copy=False,
    )
    peppol_is_demo_uuid = fields.Boolean(compute="_compute_peppol_is_demo_uuid")
    peppol_warning = fields.Html(
        string='Peppol warning',
        compute='_compute_peppol_warning',
        copy=False,
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)

        # the orm_cache does not contain the new selections added in stable: clear the cache once
        peppol_move_state_field = self._fields['peppol_move_state']
        if ('skipped', "Skipped") not in peppol_move_state_field.get_description(self.env)['selection']:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection']._update_selection(
                'account.move', 'peppol_move_state', peppol_move_state_field.selection)
            self.env.registry.clear_cache()
        return res

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to PEPPOL"))
        self.peppol_move_state = 'canceled'
        self.send_and_print_values = False

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('peppol_message_uuid')
    def _compute_peppol_is_demo_uuid(self):
        for move in self:
            move.peppol_is_demo_uuid = (move.peppol_message_uuid or '').startswith('demo_')

    @api.depends('state')
    def _compute_peppol_move_state(self):
        for move in self:
            if all([
                move.company_id.account_peppol_proxy_state == 'active',
                move.partner_id.account_peppol_is_endpoint_valid,
                move.state == 'posted',
                not move.peppol_move_state,
            ]):
                move.peppol_move_state = 'ready'
            else:
                move.peppol_move_state = move.peppol_move_state

    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.product_id', 'partner_id.peppol_eas', 'partner_id.peppol_endpoint')
    def _compute_peppol_warning(self):
        for move in self:
            if any([move.company_id.account_peppol_proxy_state != 'active',
                    move.peppol_move_state in ('skipped', 'canceled', 'done'),
                    move.partner_id.ubl_cii_format in (False, 'facturx'),
                    move.move_type not in ('out_invoice', 'out_refund'),
                    not move.restrict_mode_hash_table,
                ]):
                move.peppol_warning = None
                continue

            required_checks = {
                'partner_eas_endpoint_missing': [False, _("The partner is missing Peppol EAS code or Peppol Endpoint.")],
                'product_missing': [False, _("Each Peppol invoice line should have a corresponding product.")],
                'not_one_tax': [False, _("Each Peppol invoice line should have one and only one corresponding tax.")],
            }
            if not move.partner_id.peppol_eas or not move.partner_id.peppol_endpoint:
                required_checks['partner_eas_endpoint_missing'][0] = True
            for line in move.invoice_line_ids:
                if not line.product_id:
                    required_checks['product_missing'][0] = True
                if not line.tax_ids or len(line.tax_ids) > 1:
                    required_checks['not_one_tax'][0] = True

            move.peppol_warning = ("").join(
                f'<div>{check_val[1]}</div>' for check_val in required_checks.values() if check_val[0])
