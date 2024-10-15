# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons import website_sale


class Website(website_sale.Website):

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Members'), self.env['ir.http']._url_for('/members'), 'website_membership'))
        return suggested_controllers
