# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Website(models.Model):
    _inherit = "website"

    @api.model
    def payment_options(self):
        """ This function returns the list of payment options which are supported by payment acquirers that are published
        """
        options = self.env['payment.option'].sudo().search([('acquirer_ids', '!=', False)])
        return [opt for opt in options if any(acq.website_published for acq in opt.acquirer_ids)]
