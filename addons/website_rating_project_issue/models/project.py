# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Project(models.Model):

    _name = "project.project"
    _inherit = ['project.project', 'website.published.mixin']

    @api.multi
    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website project page """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Projcet Rating Page",
            'target': 'self',
            'url': "/project/rating/%s" % (self.id,)
        }

    @api.multi
    def _compute_website_url(self):
        super(Project, self)._compute_website_url()
        for project in self:
            project.website_url = "/project/rating/%s" % project.id
