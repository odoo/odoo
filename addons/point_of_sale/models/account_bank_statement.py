# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved

from openerp.osv import fields, osv


class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {
        'pos_session_id' : fields.many2one('pos.session', string="Session", copy=False),
        'account_id': fields.related('journal_id', 'default_debit_account_id', type='many2one', relation='account.account', readonly=True),
    }


class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    _columns= {
        'pos_statement_id': fields.many2one('pos.order', string="POS statement", ondelete='cascade'),
    }
