# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class ResCompany(osv.Model):
    _inherit = "res.company"

    def _get_tenpay_account(self, cr, uid, ids, name, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        tenpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('name', 'ilike', 'tenpay'),
            ('company_id', '=', company_id),
        ], limit=1, context=context)
        if tenpay_ids:
            tenpay = Acquirer.browse(cr, uid, tenpay_ids[0], context=context)
            return dict.fromkeys(ids, tenpay.tenpay_partner_account)
        return dict.fromkeys(ids, False)

    def _set_tenpay_account(self, cr, uid, id, name, value, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        tenpay_account = self.browse(cr, uid, id, context=context).tenpay_account
        tenpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('tenpay_partner_account', '=', tenpay_account),
            ('company_id', '=', company_id),
        ], context=context)
        if tenpay_ids:
            Acquirer.write(cr, uid, tenpay_ids, {'tenpay_partner_account': value}, context=context)
        return True

    _columns = {
        'tenpay_account': fields.function(
            _get_tenpay_account,
            fnct_inv=_set_tenpay_account,
            nodrop=True,
            type='char', string='Tenpay Account',
            help="Tenpay username (usually email) for receiving online payments."
        ),
    }
