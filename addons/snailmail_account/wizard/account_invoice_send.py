# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceSend(models.TransientModel):
    _name = 'account.invoice.send'
    _inherit = 'account.invoice.send'
    _description = 'Account Invoice Send'

    partner_id = fields.Many2one('res.partner', compute='_get_partner', string='Partner')
    snailmail_is_letter = fields.Boolean('Send by Post', help='Allows to send the document by Snailmail (coventional posting delivery service)', default=lambda self: self.env.company.invoice_is_snailmail)
    snailmail_cost = fields.Float(string='Stamp(s)', compute='_compute_snailmail_cost', readonly=True)
    invalid_addresses = fields.Integer('Invalid Addresses Count', compute='_compute_invalid_addresses')
    invalid_invoice_ids = fields.Many2many('account.move', string='Invalid Addresses', compute='_compute_invalid_addresses')

    @api.depends('invoice_ids')
    def _compute_invalid_addresses(self):
        for wizard in self:
            invalid_invoices = wizard.invoice_ids.filtered(lambda i: not self.env['snailmail.letter']._is_valid_address(i.partner_id))
            wizard.invalid_invoice_ids = invalid_invoices
            wizard.invalid_addresses = len(invalid_invoices)

    @api.depends('invoice_ids')
    def _get_partner(self):
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

        self.invoice_ids.filtered(lambda inv: not inv.invoice_sent).write({'invoice_sent': True})
        if len(self.invoice_ids) == 1:
            letters._snailmail_print()
        else:
            letters._snailmail_print(immediate=False)

    def send_and_print_action(self):
        if self.snailmail_is_letter:
            if self.invalid_addresses and self.composition_mode == "mass_mail":
                self.notify_invalid_addresses()
            self.snailmail_print_action()
        res = super(AccountInvoiceSend, self).send_and_print_action()
        return res

    def notify_invalid_addresses(self):
        self.ensure_one()
        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
            {'type': 'snailmail_invalid_address', 'title': _("Invalid Addresses"),
            'message': _("%s of the selected invoice(s) had an invalid address and were not sent") % self.invalid_addresses}
        )

    def invalid_addresses_action(self):
        return {
            'name': _('Invalid Addresses'),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.mapped('invalid_invoice_ids').ids)],
        }
