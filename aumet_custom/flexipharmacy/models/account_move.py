# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    pos_vendor_commission_ids = fields.One2many('pos.doctor.commission', 'invoice_id', String='Commission')

    @api.model
    def _get_invoice_in_payment_state(self):
        for pos_vendor_commission_id in self.pos_vendor_commission_ids:
            pos_vendor_commission_id.write({
                'state': 'paid'
            })
        return super(AccountMove, self)._get_invoice_in_payment_state()

    def button_cancel(self):
        self.write({'auto_post': False, 'state': 'cancel'})
        for pos_vendor_commission_id in self.pos_vendor_commission_ids:
            pos_vendor_commission_id.write({
                'state': 'cancelled'
            })
        return super(AccountMove, self).button_cancel()

    def button_draft(self):
        for pos_vendor_commission_id in self.pos_vendor_commission_ids:
            pos_vendor_commission_id.write({
                'state': 'reserved'
            })
        return super(AccountMove, self).button_draft()



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_wallet = fields.Boolean("Is Wallet")
    pos_vendor_commission_ids = fields.One2many('pos.doctor.commission', 'invoice_id', String='Commission')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
