# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr

from openerp.osv import fields, osv


class account_bilan_report(osv.osv_memory):
    _name = 'account.bilan.report'
    _description = 'Account Bilan Report'

    def _get_default_fiscalyear(self, cr, uid, context=None):
        fiscalyear_id = self.pool.get('account.fiscalyear').find(cr, uid)
        return fiscalyear_id

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
    }

    _defaults = {
        'fiscalyear_id': _get_default_fiscalyear
    }

    def print_bilan_report(self, cr, uid, ids, context=None):
        active_ids = context.get('active_ids', [])
        data = {}
        data['form'] = {}
        data['ids'] = active_ids
        data['form']['fiscalyear_id'] = self.browse(cr, uid, ids)[0].fiscalyear_id.id
        return self.pool['report'].get_action(
            cr, uid, ids, 'l10n_fr.report_l10nfrbilan', data=data, context=context
        )
