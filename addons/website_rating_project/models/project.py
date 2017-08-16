# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Project(models.Model):

    _name = "project.project"
    _inherit = ['project.project']

    portal_show_rating = fields.Boolean('Rating visible in Website', copy=False, oldname='website_published')

    @api.multi
    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website project page """
        self.ensure_one()
        if self.portal_show_rating:
            return {
                'type': 'ir.actions.act_url',
                'name': "Redirect to the Website Projcet Rating Page",
                'target': 'self',
                'url': "/project/rating/%s" % (self.id,)
            }
        return super(Project, self).action_view_all_rating()
