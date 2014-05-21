# -*- coding: utf-8 -*-
from openerp.osv import orm


class Website(orm.Model):
    _inherit = 'website'

    def get_partner_white_list_fields(self, cr, uid, ids, context=None):
        fields = super(Website, self).get_partner_white_list_fields(cr, uid, ids, context=context)
        fields += ["grade_id"]
        return fields
