# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

class membership_membership_line(osv.Model):
    _inherit = 'membership.membership_line'

    def get_published_companies(self, cr, uid, ids, limit=None, context=None):
        if not ids:
            return []
        limit_clause = '' if limit is None else ' LIMIT %d' % limit
        cr.execute('SELECT DISTINCT p.id \
                    FROM res_partner p INNER JOIN membership_membership_line m \
                    ON  p.id = m.partner \
                    WHERE website_published AND is_company AND m.id IN %s ' + limit_clause, (tuple(ids),))
        return [partner_id[0] for partner_id in cr.fetchall()]
