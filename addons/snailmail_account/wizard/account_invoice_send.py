# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceSend(models.TransientModel):
    _name = 'account.invoice.send'
    _inherit = 'account.invoice.send'
    _description = 'Account Invoice Send'

    partner_id = fields.Many2one('res.partner', compute='_get_partner', string='Partner')
    snailmail_is_letter = fields.Boolean('Send by Post', help='Allows to send the document by snail mail (coventional posting delivery service)', default=lambda self: self.env.user.company_id.invoice_is_snailmail)
    snailmail_cost = fields.Float(string='Stamp(s)', compute='_snailmail_estimate', store=True, readonly=True)
    letter_ids = fields.Many2many('snailmail.letter', 'snailmail_letter_account_invoice_send_rel', ondelete='cascade')
    invalid_addresses = fields.Integer('Invalid Addresses', compute='_compute_invalid_addresses')

    @api.depends('snailmail_cost', 'letter_ids')
    def _compute_invalid_addresses(self):
        for wizard in self:
            count_invalid_addresses = 0
            required_fields = ['street', 'city', 'zip', 'country_id']
            for letter in wizard.letter_ids:
                for field in required_fields:
                    if not letter.partner_id[field]:
                        count_invalid_addresses += 1
                        break
            wizard.invalid_addresses = count_invalid_addresses

    @api.multi
    @api.onchange('invoice_ids')
    def _get_invoice_currency(self):
        for wizard in self:
            if wizard.invoice_ids:
                wizard.currency_id = wizard.invoice_ids.mapped('currency_id')[0].id

    @api.multi
    @api.onchange('invoice_ids')
    def _get_partner(self):
        for wizard in self:
            if wizard.invoice_ids and len(wizard.invoice_ids) == 1:
                wizard.partner_id = wizard.invoice_ids.partner_id.id

    @api.multi
    def unlink(self):
        for agc in self:
            agc.letter_ids.filtered(lambda l: l.state == 'draft').unlink()
        return super(AccountInvoiceSend, self).unlink()

    @api.multi
    def _fetch_letters(self):
        self.ensure_one()
        if not self.letter_ids:

            letters = self.env['snailmail.letter']
            for invoice in self.invoice_ids:
                letter = letters.create({
                    'partner_id': invoice.partner_id.id,
                    'model': 'account.invoice',
                    'res_id': invoice.id,
                    'user_id': self.env.user.id,
                    'company_id': invoice.company_id.id,
                    'report_template': self.env.ref('account.account_invoices').id
                })
                letters |= letter
            self.letter_ids = [(4, l.id) for l in letters]
        return self.letter_ids

    @api.onchange('snailmail_is_letter')
    def _snailmail_estimate(self):
        for wizard in self:
            if wizard.snailmail_is_letter:
                letters = wizard._fetch_letters()
                wizard.snailmail_cost = letters._snailmail_estimate()

    @api.multi
    def snailmail_print_action(self):
        for wizard in self:
            letters = wizard._fetch_letters()
            letters.write({'state': 'pending'})
            wizard.invoice_ids.filtered(lambda inv: not inv.sent).write({'sent': True})
            if len(letters) == 1:
                letters._snailmail_print()

    @api.multi
    def send_and_print_action(self):
        if self.snailmail_is_letter and self.invalid_addresses:
            if self.composition_mode == "mass_mail":
                self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                            {'type': 'snailmail_invalid_address', 'title': _("Invalid Addresses"),
                            'message': _("%s of the selected invoice(s) had an invalid address and were not sent") % self.invalid_addresses}
                        )
            else:
                raise UserError(_(
                    '''Cannot send by post to an incomplete address.
                    Please update the customer's address or uncheck \'Send by Post\'.'''
                ))
        res = super(AccountInvoiceSend, self).send_and_print_action()
        if self.snailmail_is_letter:
            self.snailmail_print_action()
        return res
