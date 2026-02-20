# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.account.models.company import PEPPOL_MAILING_COUNTRIES


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID', copy=False)
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

    @api.depends('peppol_message_uuid')
    def _compute_peppol_is_demo_uuid(self):
        for move in self:
            move.peppol_is_demo_uuid = (move.peppol_message_uuid or '').startswith('demo_')

    @api.depends('state')
    def _compute_peppol_move_state(self):
        for move in self:
            if all([
                move.company_id.account_peppol_proxy_state == 'active',
                move.commercial_partner_id.account_peppol_is_endpoint_valid,
                move.state == 'posted',
                move.move_type in ('out_invoice', 'out_refund', 'out_receipt'),
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

    @api.depends('peppol_message_uuid')
    def _compute_duplicated_ref_ids(self):
        return super()._compute_duplicated_ref_ids()

    def _fetch_duplicate_supplier_reference(self, only_posted=False):
        # We check whether there are moves with the same peppol message uuid
        peppol_vendor_bills = self.filtered(lambda m: m.is_purchase_document() and m.peppol_message_uuid and m._origin.id)
        if not peppol_vendor_bills:
            return super()._fetch_duplicate_supplier_reference(only_posted=only_posted)

        self.env['account.move'].flush_model(('company_id', 'move_type', 'peppol_message_uuid'))

        self.env.cr.execute(
            """
              SELECT move.id AS move_id,
                     ARRAY_AGG(duplicate_move.id) AS duplicate_ids
                FROM account_move AS move
                JOIN account_move AS duplicate_move
                  ON move.company_id = duplicate_move.company_id
                 AND move.move_type = duplicate_move.move_type
                 AND move.id != duplicate_move.id
                 AND move.peppol_message_uuid = duplicate_move.peppol_message_uuid
               WHERE move.id IN %(moves)s
            GROUP BY move.id
            """,
            {
                'moves': tuple(peppol_vendor_bills.ids),
            },
        )
        peppol_message_duplicates = {
            self.env['account.move'].browse(res['move_id']): self.env['account.move'].browse(res['duplicate_ids'])
            for res in self.env.cr.dictfetchall()
        }
        move_duplicates = super()._fetch_duplicate_supplier_reference(only_posted=only_posted)
        for move, duplicates in peppol_message_duplicates.items():
            move_duplicates[move] = move_duplicates.get(move, self.env['account.move']) | duplicates
        return move_duplicates

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        invoice = render_context['record']
        invoice_country = invoice.commercial_partner_id.country_code
        company_country = invoice.company_id.country_code
        company_on_peppol = invoice.company_id.account_peppol_proxy_state == 'active'
        if company_on_peppol and company_country in PEPPOL_MAILING_COUNTRIES and invoice_country in PEPPOL_MAILING_COUNTRIES:
            render_context['peppol_info'] = {
                'peppol_country': invoice_country,
                'is_peppol_sent': invoice.peppol_move_state in ('processing', 'done'),
                'partner_on_peppol': invoice.commercial_partner_id.account_peppol_is_endpoint_valid,
            }
        return render_context
