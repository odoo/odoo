# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class ResCompany(osv.Model):
    _inherit = "res.company"

    def _get_paypal_account(self, cr, uid, ids, name, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        paypal_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('name', 'ilike', 'paypal'),
            ('company_id', '=', company_id),
        ], limit=1, context=context)
        if paypal_ids:
            paypal = Acquirer.browse(cr, uid, paypal_ids[0], context=context)
            return dict.fromkeys(ids, paypal.paypal_email_account)
        return dict.fromkeys(ids, False)

    def _set_paypal_account(self, cr, uid, id, name, value, arg, context=None):
        Acquirer = self.pool['payment.acquirer']
        company_id = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.id
        paypal_account = self.browse(cr, uid, id, context=context).paypal_account
        paypal_ids = Acquirer.search(cr, uid, [
            ('website_published', '=', True),
            ('paypal_email_account', '=', paypal_account),
            ('company_id', '=', company_id),
        ], context=context)
        if paypal_ids:
            Acquirer.write(cr, uid, paypal_ids, {'paypal_email_account': value}, context=context)
        return True

    _columns = {
        'paypal_account': fields.function(
            _get_paypal_account,
            fnct_inv=_set_paypal_account,
            nodrop=True,
            type='char', string='Paypal Account',
            help="Paypal username (usually email) for receiving online payments."
        ),
    }
