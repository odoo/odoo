# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class gamification_challenge(osv.Model):
    _inherit = 'gamification.challenge'

    def _get_categories(self, cr, uid, context=None):
        res = super(gamification_challenge, self)._get_categories(cr, uid, context=context)
        res.append(('forum', 'Website / Forum'))
        return res


class Badge(osv.Model):
    _inherit = 'gamification.badge'
    _columns = {
        'level': fields.selection([('bronze', 'bronze'), ('silver', 'silver'), ('gold', 'gold')], 'Forum Badge Level'),
    }
