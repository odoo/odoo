# -*- encoding: utf-8 -*-

from osv import osv
import netsvc

class res_partner(osv.osv):
    _inherit='res.partner'

    def __getattr__(self, attr):
        if not attr.startswith('check_vat_'):
            super(res_partner, self).__getattr__(attr)

        def validar_nit(numero):
            return True
        return validar_nit

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
