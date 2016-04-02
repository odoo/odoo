# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp.addons.website.models.website import slug


class res_partner_grade(osv.osv):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    _defaults = {
        'website_published': True,
    }

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(res_partner_grade, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for grade in self.browse(cr, uid, ids, context=context):
            res[grade.id] = "/partners/grade/%s" % (slug(grade))
        return res
