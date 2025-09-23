# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'city_id', 'street_name', 'street_number', 'street_number2'})

        return frontend_writable_fields
