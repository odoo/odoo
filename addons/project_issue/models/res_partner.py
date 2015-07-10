# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_partner(osv.osv):
    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        return {
            partner_id: Issue.search_count(cr,uid, [('partner_id', '=', partner_id)])
            for partner_id in ids
        }

    """ Inherits partner and adds Issue information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'issue_count': fields.function(_issue_count, string='# Issues', type='integer'),
    }
