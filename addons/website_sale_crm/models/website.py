# -*- coding: utf-8 -*-
from openerp.osv import orm
from openerp import SUPERUSER_ID


class Website(orm.Model):
    _inherit = 'website'

    def _ecommerce_create_quotation(self, cr, uid, context=None):
        order_id = super(Website, self)._ecommerce_create_quotation(cr, uid, context=context)
        section_ids = self.pool["crm.case.section"].search(cr, SUPERUSER_ID, [("code", "=", "Website")], context=context)
        if section_ids:
            self.pool["sale.order"].write(cr, SUPERUSER_ID, {'section_id': section_ids[0]}, context=context)
        return order_id
