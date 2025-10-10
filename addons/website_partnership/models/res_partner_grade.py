# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _inherit = ['res.partner.grade', 'website.published.mixin']

    def _compute_website_url(self):
        super()._compute_website_url()
        for grade in self:
            grade.website_url = "/partners/grade/%s" % (self.env['ir.http']._slug(grade))

    def _default_is_published(self):
        return True
