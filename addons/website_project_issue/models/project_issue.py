# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import _, api, models


class Issue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue']

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/issues/%s' % self.id,
            'target': 'self',
            'res_id': self.id,
        }
