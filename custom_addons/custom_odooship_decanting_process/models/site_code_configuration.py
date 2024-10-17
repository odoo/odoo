# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api



class SiteCodeConfiguration(models.Model):
    _name = 'site.code.configuration'
    _description = 'Site Code Configuration.'

    name = fields.Char(string='Site Code')

