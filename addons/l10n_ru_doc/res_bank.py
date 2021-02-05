# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2014-2018 CodUP (<http://codup.com>).
#
##############################################################################

from odoo import api, fields, models

class Bank(models.Model):
    _inherit = 'res.bank'

    corr_acc = fields.Char('Corresponding account', size=64)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_corr_acc = fields.Char('Corresponding account', size=64)

    @api.onchange('bank_id')
    def onchange_bank_id(self):
        self.bank_name = self.bank_id.name
        self.bank_bic = self.bank_id.bic
        self.bank_corr_acc = self.bank_id.corr_acc
