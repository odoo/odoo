# -*- coding: utf-8 -*-
from openerp.models import AbstractModel

class publisher_warranty_contract(AbstractModel):
    _inherit = "publisher_warranty.contract"

    def _get_message(self, cr, uid):
        msg = super(publisher_warranty_contract, self)._get_message(cr, uid)
        msg['website'] = True
        return msg
