# -*- coding: utf-8 -*-

from odoo import api, fields, models

class Job(models.Model):

    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.mixin']

    website_description = fields.Html('Website description', translate=True)

    @api.multi
    def _website_url(self, field_name, arg):
        result = super(Job, self)._website_url(field_name, arg)
        for job in self:
            result[job.id] = "/jobs/detail/%s" % job.id
        return result

    @api.multi
    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()
