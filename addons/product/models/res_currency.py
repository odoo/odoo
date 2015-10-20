    # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.tools.float_utils import float_compare


class res_currency(osv.osv):
    _inherit = 'res.currency'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT digits FROM decimal_precision WHERE name like %s', ('Account',))
        digits = cr.fetchone()
        if digits and len(digits):
            digits = digits[0]
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for currency_id in ids:
                if currency_id == main_currency.id:
                    if float_compare(main_currency.rounding, 10 ** -digits, precision_digits=6) == -1:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'.', ['rounding']),
    ]
