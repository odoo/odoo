# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    address_full = fields.Char("Full Address", compute="_compute_address_full")
    rate_to_khr = fields.Float(string="Rate to Cambodia Riel", compute="_compute_rate_to_khr")

    def _compute_rate_to_khr(self):
        khr = self.env.ref('base.KHR')
        for rec in self:
            # khr.rate = amount of company's currency for 1 KHR, so we use khr.inverse_rate
            rec.rate_to_khr = khr.inverse_rate

    def _compute_address_full(self):
        address_fields = self._get_company_address_field_names()
        non_empty_vals = []
        for field in address_fields:
            if field in ['country_id', 'state_id'] and self[field].name:
                non_empty_vals.append(self[field].name)
            elif self[field]:
                non_empty_vals.append(self[field])
        self.address_full = ", ".join(non_empty_vals)
