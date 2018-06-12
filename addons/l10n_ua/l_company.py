# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class res_company(osv.osv):
    _name = 'res.company'
    _inherit = 'res.company'

    _columns = {
        'company_registry': fields.related('partner_id', 'company_registry',
                                           string=u"ЄДРПОУ",
                                           type="char",
                                           size=10)
    }

res_company()
