# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = ['base.vat.mixin', 'res.partner']
    _name = 'res.partner'
