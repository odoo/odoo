# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
