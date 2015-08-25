# -*- coding: utf-8 -*-
from openerp import api, fields, models


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
    def _website_url(self, field_name, arg):
        res = dict()
        for project in self:
            res[project.id] = "/project/rating/%s" % project.id
        return res
