# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    region_id = fields.Many2one('account.intrastat.region', string='Intrastat region')
    transport_mode_id = fields.Many2one('account.intrastat.transport', string='Default transport mode')
    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm for Intrastat',
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')
