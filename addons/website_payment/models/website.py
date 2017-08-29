# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Website(models.Model):
    _inherit = "website"

    @api.model
    def payment_icons(self):
        """ This function returns the list of payment icons which are supported by payment acquirers that are published
        """
        icons = self.env['payment.icon'].sudo().search([('acquirer_ids', '!=', False)])
        return [icon for icon in icons if any(acq.website_published for acq in icon.acquirer_ids)]
