# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class ResCompany(osv.Model):
    _inherit = "res.company"

    def _get_alipay_account(self, cr, uid, ids, name, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        alipay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('name', 'ilike', 'alipay'),
            ('company_id', '=', company_id),
        ], limit=1, context=context)
        if alipay_ids:
            alipay = Acquirer.browse(cr, uid, alipay_ids[0], context=context)
            return dict.fromkeys(ids, alipay.alipay_partner_account)
        return dict.fromkeys(ids, False)

    def _set_alipay_account(self, cr, uid, id, name, value, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        alipay_account = self.browse(cr, uid, id, context=context).alipay_account
        alipay_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('alipay_partner_account', '=', alipay_account),
            ('company_id', '=', company_id),
        ], context=context)
        if alipay_ids:
            Acquirer.write(cr, uid, alipay_ids, {'alipay_partner_account': value}, context=context)
        return True

    _columns = {
        'alipay_account': fields.function(
            _get_alipay_account,
            fnct_inv=_set_alipay_account,
            nodrop=True,
            type='char', string='Alipay Account',
            help="Alipay username (usually email) for receiving online payments."
        ),
    }
