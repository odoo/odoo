# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields



class CrateContainerConfiguration(models.Model):
    _name = 'crate.container.configuration'
    _description = 'Crate Container Configuration'

    name = fields.Char(string='Reference', required=True)
    crate_container_partition = fields.Integer(string='Partition', required=True)
    crate_code = fields.Char(string='Code')
