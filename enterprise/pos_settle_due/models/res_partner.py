# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_total_due(self, pos_currency):
        pos_payments = self.env['pos.order'].search([
            ('partner_id', '=', self.id), ('state', '=', 'paid'),
            ('session_id.state', '!=', 'closed')]).mapped('payment_ids')
        total_settled = sum(pos_payments.filtered_domain(
            [('payment_method_id.type', '=', 'pay_later')]).mapped('amount'))

        self_sudo = self
        group_pos_user = self.env.ref('point_of_sale.group_pos_user')
        if group_pos_user in self.env.user.groups_id:
            self_sudo = self.sudo()  # allow POS users without accounting rights to settle dues

        total_due = self_sudo.parent_id.total_due if self.parent_id else self_sudo.total_due
        total_due += total_settled
        if self.env.company.currency_id.id != pos_currency:
            pos_currency = self.env['res.currency'].browse(pos_currency)
            return self.env.company.currency_id._convert(total_due, pos_currency, self.env.company, fields.Date.today())
        return total_due

    def get_all_total_due(self, pos_currency):
        due_amounts = {}
        for partner in self:
            due_amounts[partner.id] = partner.get_total_due(pos_currency)
        return due_amounts

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.user.has_group('account.group_account_readonly') or self.env.user.has_group('account.group_account_invoice'):
            params += ['credit_limit', 'total_due', 'use_partner_credit_limit']
        return params

    def _load_pos_data(self, data):
        response = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])

        if config_id.currency_id != self.env.company.currency_id and (self.env.user.has_group('account.group_account_readonly') or self.env.user.has_group('account.group_account_invoice')):
            for partner in response['data']:
                partner['total_due'] = self.env.company.currency_id._convert(partner['total_due'], config_id.currency_id, self.env.company, fields.Date.today())

        return response

    def _compute_has_moves(self):
        super()._compute_has_moves()
        for partner in self.filtered(lambda p: not p.has_moves):
            partner.has_moves = partner.total_due != 0
