# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from datetime import date


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        # OVERRIDE to update the cancel date.
        res = super(AccountMove, self).button_draft()
        for move in self:
            if move.move_type == 'out_invoice':
                self.env['membership.membership_line'].search([
                    ('account_invoice_line', 'in', move.mapped('invoice_line_ids').ids)
                ]).write({'date_cancel': False})
        return res

    def button_cancel(self):
        # OVERRIDE to update the cancel date.
        res = super(AccountMove, self).button_cancel()
        for move in self:
            if move.move_type == 'out_invoice':
                self.env['membership.membership_line'].search([
                    ('account_invoice_line', 'in', move.mapped('invoice_line_ids').ids)
                ]).write({'date_cancel': fields.Date.today()})
        return res

    def write(self, vals):
        # OVERRIDE to write the partner on the membership lines.
        res = super(AccountMove, self).write(vals)
        if 'partner_id' in vals:
            self.env['membership.membership_line'].search([
                ('account_invoice_line', 'in', self.mapped('invoice_line_ids').ids)
            ]).write({'partner': vals['partner_id']})
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _prepare_membership_line_data(self):
        self.ensure_one()
        date_from = self.product_id.membership_date_from
        date_to = self.product_id.membership_date_to
        if (date_from and date_from < (self.move_id.invoice_date or date.min) < (date_to or date.min)):
            date_from = self.move_id.invoice_date
        return {
            'partner': self.move_id.partner_id.id,
            'membership_id': self.product_id.id,
            'member_price': self.price_unit,
            'date': fields.Date.today(),
            'date_from': date_from,
            'date_to': date_to,
            'account_invoice_line': self.id,
        }

    def write(self, vals):
        # OVERRIDE
        res = super(AccountMoveLine, self).write(vals)

        to_process = self.filtered(lambda line: line.move_id.move_type == 'out_invoice' and line.product_id.membership)

        # Nothing to process, break.
        if not to_process:
            return res

        existing_memberships = self.env['membership.membership_line'].search([
            ('account_invoice_line', 'in', to_process.ids)])
        to_create = to_process - existing_memberships.mapped('account_invoice_line')

        memberships_vals = []
        for line in to_create:
            memberships_vals.append(line._prepare_membership_line_data())

        if memberships_vals:
            self.env['membership.membership_line'].create(memberships_vals)

        for membership in existing_memberships:
            membership.write(membership.account_invoice_line._prepare_membership_line_data())

        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        lines = super(AccountMoveLine, self).create(vals_list)
        to_process = lines.filtered(lambda line: line.move_id.move_type == 'out_invoice' and line.product_id.membership)

        # Nothing to process, break.
        if not to_process:
            return lines

        existing_memberships = self.env['membership.membership_line'].search([
            ('account_invoice_line', 'in', to_process.ids)])
        to_process = to_process - existing_memberships.mapped('account_invoice_line')

        # All memberships already exist, break.
        if not to_process:
            return lines

        memberships_vals = []
        for line in to_process:
            memberships_vals.append(line._prepare_membership_line_data())
        self.env['membership.membership_line'].create(memberships_vals)
        return lines
