# -*- coding: utf-8 -*-
# See __openerp__.py file for full copyright and licensing details.

from openerp import api, models


class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False,
                                    company_id=False):
        llc_obj = self.env['mrp.bom.llc']
        llc_obj.update_orderpoint_llc()
        if use_new_cursor:
            self._cr.commit()
        return super(procurement_order, self)._procure_orderpoint_confirm(
            use_new_cursor, company_id)
