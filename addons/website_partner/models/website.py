# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super().get_suggested_controllers()
        suggested_controllers.append((_('Partners'), self.env['ir.http']._url_for('/partners'), 'website_partner'))
        return suggested_controllers
