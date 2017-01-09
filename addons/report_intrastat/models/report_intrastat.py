# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class res_country(models.Model):
    _inherit = 'res.country'

    intrastat = fields.Boolean(string="Intrastat member")


class ReportIntrastatCode(models.Model):
    _name = "report.intrastat.code"
    _description = "Intrastat code"
    _translate = False

    name = fields.Char(string='Intrastat Code')
    description = fields.Char(string='Description')


class ProductTemplate(models.Model):
    _inherit = "product.template"

    intrastat_id = fields.Many2one('report.intrastat.code', string='Intrastat Code')
