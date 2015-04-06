# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class ResCompany(osv.Model):
    _inherit = "res.company"

    def _get_allpay_account(self, cr, uid, ids, name, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        allpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('name', 'ilike', 'allpay'),
            ('company_id', '=', company_id),
        ], limit=1, context=context)
        if allpay_ids:
            allpay = Acquirer.browse(cr, uid, allpay_ids[0], context=context)
            return dict.fromkeys(ids, allpay.allpay_partner_account)
        return dict.fromkeys(ids, False)

    def _set_allpay_account(self, cr, uid, id, name, value, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        allpay_account = self.browse(cr, uid, id, context=context).allpay_account
        allpay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('allpay_partner_account', '=', allpay_account),
            ('company_id', '=', company_id),
        ], context=context)
        if allpay_ids:
            Acquirer.write(cr, uid, allpay_ids, {'allpay_partner_account': value}, context=context)
        return True

    _columns = {
        'allpay_account': fields.function(
            _get_allpay_account,
            fnct_inv=_set_allpay_account,
            nodrop=True,
            type='char', string='allPay Account',
            help="allPay username (usually email) for receiving online payments."
        ),
    }
