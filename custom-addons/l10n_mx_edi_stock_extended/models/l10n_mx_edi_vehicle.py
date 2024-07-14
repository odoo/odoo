# -*- coding: utf-8 -*-

from odoo import models, fields

class Vehicle(models.Model):
    _inherit = 'l10n_mx_edi.vehicle'

    environment_insurer = fields.Char(
        string="Environment Insurer",
        help="The name of the insurer that covers the liability risks of the environment when transporting hazardous materials")
    environment_insurance_policy = fields.Char(
        string="Environment Insurance Policy",
        help="Environment Insurance Policy Number - used when transporting hazardous materials")
