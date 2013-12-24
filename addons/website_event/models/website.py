# -*- coding: utf-8 -*-
from openerp.osv import orm


class Website(orm.Model):
    _inherit = 'website'

    def ecommerce_get_product_domain(self):
        # remove product event from the website content grid and list view (not removed in detail view)
        return ['&'] + super(Website, self).ecommerce_get_product_domain() + [('event_ok', '=', False)]
