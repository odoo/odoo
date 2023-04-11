# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    pos_payment_method_ids = fields.One2many('pos.payment.method', 'cash_journal_id', string='Point of Sale Payment Methods')

    def _get_unlink_journals(self):
        journals = super()._get_unlink_journals()
        config_journals = self.env['pos.config'].search([('journal_id', 'in', self.ids)])
        journals |= config_journals.mapped('journal_id')
        return journals
