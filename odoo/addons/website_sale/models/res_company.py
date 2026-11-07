# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_pricelist_vals(self):
        """ Override of product. Called at company creation or activation of the pricelist setting.

        We don't want the default website from the current company to be applied on every company

        Note: self.ensure_one()

        :rtype: dict
        """
        values = super()._get_default_pricelist_vals()
        values['website_id'] = False
        return values
