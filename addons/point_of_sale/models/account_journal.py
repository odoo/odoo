# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_payment_method_ids = fields.One2many('pos.payment.method', 'journal_id', string='Point of Sale Payment Methods')

    def action_archive(self):
        if self.pos_payment_method_ids:
            raise ValidationError(_("This journal is associated with a payment method. You cannot archive it"))
        return super().action_archive()

    @api.constrains('type')
    def _check_type(self):
        methods = self.env['pos.payment.method'].sudo().search([("journal_id", "in", self.ids)])
        if methods:
            raise ValidationError(_("This journal is associated with a payment method. You cannot modify its type"))

    def _get_journal_inbound_outstanding_payment_accounts(self):
        res = super()._get_journal_inbound_outstanding_payment_accounts()
        account_ids = set(res.ids)
        for payment_method in self.sudo().pos_payment_method_ids:
            account_ids.add(payment_method.outstanding_account_id.id)
        return self.env['account.account'].browse(account_ids)

    @api.model
    def _ensure_company_account_journal(self):
        journal = self.search([
            ('code', '=', 'POSS'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not journal:
            journal = self.create({
                'name': _('Point of Sale'),
                'code': 'POSS',
                'type': 'general',
                'company_id': self.env.company.id,
            })
        return journal
