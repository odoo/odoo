# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved

from openerp.osv import fields, osv


class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
        'journal_user': fields.boolean('Active in Point of Sale', help="Check this box if this journal define a payment method that can be used in a point of sale."),

        'amount_authorized_diff' : fields.float('Amount Authorized Difference', help="This field depicts the maximum difference allowed between the ending balance and the theoretical cash when closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at the closing of his session saying that he needs to contact his manager."),
    }
