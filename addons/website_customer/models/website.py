# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons import website_crm_partner_assign


class Website(website_crm_partner_assign.Website):

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('References'), self.env['ir.http']._url_for('/customers'), 'website_customer'))
        return suggested_controllers
