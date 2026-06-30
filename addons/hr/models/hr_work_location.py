# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrWorkLocation(models.Model):
    _name = 'hr.work.location'
    _description = "Work Location"
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(string="Work Location", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    location_type = fields.Selection([
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other')], string='Cover Image', default='office', required=True)
    address_id = fields.Many2one('res.partner', required=True, string="Work Address", check_company=True)
    location_number = fields.Char()
