# -*- coding: utf-8 -*-
from odoo import fields, models


class ExternalProvider(models.Model):
    _name = "external.provider"
    _description = "External Provider"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    city = fields.Char(string="City")
    state = fields.Char(string="State", size=2)
    npi = fields.Char(string="NPI", index=True)
    company = fields.Char(string="Company")
    license = fields.Char(string="License")
    taxonomy = fields.Char(string="Taxonomy")
