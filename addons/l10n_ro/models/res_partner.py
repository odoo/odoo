# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>
# Copyright (C) 2020 NextERP Romania (https://www.nexterp.ro) <contact@nexterp.ro>
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['nrc']

    nrc = fields.Char(string='NRC', help='Registration number at the Registry of Commerce')
