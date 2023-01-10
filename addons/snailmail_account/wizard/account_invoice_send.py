# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class AccountInvoiceSend(models.TransientModel):
    _name = 'account.invoice.send'
    _inherit = 'account.invoice.send'
    _description = 'Account Invoice Send'

    partner_id = fields.Many2one('res.partner', compute='_get_partner', string='Partner')
    snailmail_is_letter = fields.Boolean('Send by Post',
        help='Allows to send the document by Snailmail (conventional posting delivery service)',
        default=lambda self: self.env.company.invoice_is_snailmail)
    snailmail_cost = fields.Float(string='Stamp(s)', compute='_compute_snailmail_cost', readonly=True)
    invalid_addresses = fields.Integer('Invalid Addresses Count', compute='_compute_invalid_addresses')
    invalid_invoices = fields.Integer('Invalid Invoices Count', compute='_compute_invalid_addresses')
    invalid_partner_ids = fields.Many2many('res.partner', string='Invalid Addresses', compute='_compute_invalid_addresses')

    @api.depends('invoice_ids')
    def _compute_invalid_addresses(self):
        for wizard in self:
            if any(not invoice.partner_id for invoice in wizard.invoice_ids):
                raise UserError(_('You cannot send an invoice which has no partner assigned.'))
            invalid_invoices = wizard.invoice_ids.filtered(lambda i: not self.env['snailmail.letter']._is_valid_address(i.partner_id))
            wizard.invalid_invoices = len(invalid_invoices)
            invalid_partner_ids = invalid_invoices.partner_id.ids
            wizard.invalid_addresses = len(invalid_partner_ids)
            wizard.invalid_partner_ids = [Command.set(invalid_partner_ids)]

    @api.depends('invoice_ids')
    def _get_partner(self):
        self.partner_id = self.env['res.partner']
        for wizard in self:
            if wizard.invoice_ids and len(wizard.invoice_ids) == 1:
                wizard.partner_id = wizard.invoice_ids.partner_id.id

    @api.depends('snailmail_is_letter')
    def _compute_snailmail_cost(self):
        for wizard in self:
            wizard.snailmail_cost = len(wizard.invoice_ids.ids)

    def snailmail_print_action(self):
        self.ensure_one()
        letters = self.env['snailmail.letter']
        for invoice in self.invoice_ids:
            letter = self.env['snailmail.letter'].create({
                'partner_id': invoice.partner_id.id,
                'model': 'account.move',
                'res_id': invoice.id,
                'user_id': self.env.user.id,
                'company_id': invoice.company_id.id,
                'report_template': self.env.ref('account.account_invoices').id
            })
            letters |= letter

        self.invoice_ids.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        if len(self.invoice_ids) == 1:
            letters._snailmail_print()
        else:
            letters._snailmail_print(immediate=False)

    def send_and_print_action(self):
        if self.snailmail_is_letter:
            if self.env['snailmail.confirm.invoice'].show_warning():
                wizard = self.env['snailmail.confirm.invoice'].create({'model_name': _('Invoice'), 'invoice_send_id': self.id})
                return wizard.action_open()
            self._print_action()
        return self.send_and_print()
    
    def _print_action(self):
        if not self.snailmail_is_letter:
            return

        if self.invalid_addresses and self.composition_mode == "mass_mail":
            self.notify_invalid_addresses()
        self.snailmail_print_action()

    def send_and_print(self):
        res = super(AccountInvoiceSend, self).send_and_print_action()
        return res

    def notify_invalid_addresses(self):
        self.ensure_one()
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'snailmail_invalid_address', {
            'title': _("Invalid Addresses"),
            'message': _("%s of the selected invoice(s) had an invalid address and were not sent", self.invalid_invoices),
        })

    def invalid_addresses_action(self):
        return {
            'name': _('Invalid Addresses'),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'res.partner',
            'domain': [('id', 'in', self.invalid_partner_ids.ids)],
        }
