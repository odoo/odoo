# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Project(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'website.published.mixin']

    def action_view_all_rating(self):
        if self.website_published:
            return self.open_website_url()
        return super(Project, self).action_view_all_rating()

    def open_website_url(self):
        """ return the action to see all the rating of the project, and activate default filters """
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Project Rating Page",
            'target': 'self',
            'url': "/project/rating/%s" % (self.id)
        }
