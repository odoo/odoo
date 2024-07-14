# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_fleet_settings = fields.Boolean(
        related='company_id.documents_fleet_settings', readonly=False, string="Fleet")
    documents_fleet_folder = fields.Many2one(
        'documents.folder', related='company_id.documents_fleet_folder', readonly=False, string="Fleet Workspace")
    documents_fleet_tags = fields.Many2many(
        'documents.tag', related='company_id.documents_fleet_tags', readonly=False, string="Fleet Default Tags")
