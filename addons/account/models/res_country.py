# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCountry(models.Model):
    _inherit = 'res.country'

    # adding abstract method to be overridden
    def _set_intrastat_from_partner():
        pass

