# -*- coding: utf-8 -*-
from openerp.osv import orm


class Website(orm.Model):
    _inherit = 'website'

    def sale_product_domain(self, cr, uid, ids, context=None):
        # remove product event from the website content grid and list view (not removed in detail view)
        return ['&'] + super(Website, self).sale_product_domain(cr, uid, ids, context=context) + [('event_ok', '=', False)]
