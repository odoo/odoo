# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ldap
from openerp.osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'ldaps': fields.one2many(
            'res.company.ldap', 'company', 'LDAP Parameters', copy=True, groups="base.group_system"),
    }