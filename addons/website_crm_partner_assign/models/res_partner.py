# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.addons.website.models.website import slug


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    website_published = fields.Boolean(default=True)

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(ResPartnerGrade, self)._website_url(field_name, arg)
        for grade in self:
            res[grade.id] = "/partners/grade/%s" % (slug(grade))
        return res
