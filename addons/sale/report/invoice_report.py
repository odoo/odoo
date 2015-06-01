# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields,osv

class account_invoice_report(osv.osv):
    _inherit = 'account.invoice.report'
    _columns = {
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id'),
    }
    _depends = {
        'account.invoice': ['team_id'],
    }

    def _select(self):
        return  super(account_invoice_report, self)._select() + ", sub.team_id as team_id"

    def _sub_select(self):
        return  super(account_invoice_report, self)._sub_select() + ", ai.team_id as team_id"

    def _group_by(self):
        return super(account_invoice_report, self)._group_by() + ", ai.team_id"
