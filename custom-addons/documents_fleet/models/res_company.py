# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_fleet_settings = fields.Boolean(default=True)
    documents_fleet_folder = fields.Many2one(
        'documents.folder',
        string="Fleet Workspace",
        default=lambda self: self.env.ref('documents_fleet.documents_fleet_folder', raise_if_not_found=False),
        domain="['|', ('company_id', '=', False), ('company_id', '=', id)]",
    )
    documents_fleet_tags = fields.Many2many('documents.tag', 'documents_fleet_tags_table')
