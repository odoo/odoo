# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = ['base.vat.mixin', 'account.fiscal.position']
    _name = 'account.fiscal.position'

    _base_vat_vat_field = 'foreign_vat'

    @api.depends('vat_country_id')
    def _constrains_vat_country(self):
        super()._constrains_vat_country()
        for record in self:
            if record.vat_country_id and record.vat_country_id != record.country_id:
                raise ValidationError(_("The country detected for this foreign VAT number does not match the one set on this fiscal position."))
