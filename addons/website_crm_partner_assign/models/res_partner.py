# -*- coding: utf-8 -*-
from openerp import api
from openerp.osv import osv
from openerp.addons.website.models.website import slug


class res_partner_grade(osv.osv):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    _defaults = {
        'website_published': True,
    }

    @api.multi
    @api.depends('name')
    def _website_url(self):
        super(res_partner_grade, self)._website_url()
        for grade in self:
            grade.website_url = "/partners/grade/%s" % (slug(grade))
