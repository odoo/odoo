# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.one
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the online quote if exists. """
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/orders/%s' % self.id,
            'target': 'self',
            'res_id': self.id,
        }
