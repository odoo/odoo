# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    website_ids = fields.One2many('website', 'salesteam_id', string='Websites', help="Websites using this sales team")
