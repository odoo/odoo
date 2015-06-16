# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved

from openerp.osv import fields, osv

class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
        'journal_user': fields.boolean('PoS Payment Method', help="Check this box if this journal define a payment method that can be used in point of sales."),

        'amount_authorized_diff' : fields.float('Amount Authorized Difference', help="This field depicts the maximum difference allowed between the ending balance and the theorical cash when closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at the closing of his session saying that he needs to contact his manager."),
        'self_checkout_payment_method' : fields.boolean('Self Checkout Payment Method'), #FIXME : this field is obsolete
    }
    _defaults = {
        'self_checkout_payment_method' : False,
    }


class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {
        'pos_session_id' : fields.many2one('pos.session', string="Session", copy=False),
        'account_id': fields.related('journal_id', 'default_debit_account_id', type='many2one', relation='account.account', readonly=True),
    }
