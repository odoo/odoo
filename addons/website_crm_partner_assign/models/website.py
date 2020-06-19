# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Resellers'), url_for('/partners'), 'website_crm_partner_assign'))
        return suggested_controllers
