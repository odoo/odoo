# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.constrains('active', 'key', 'website_id')
    def _check_active(self):
        for record in self:
            if record.key == 'website_sale.address_b2b' and record.website_id:
                if record.website_id.company_id.country_id.code == "AR" and not record.active:
                    raise ValidationError(_("B2B fields must always be displayed with Argentinian website."))
