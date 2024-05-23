#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_project_mrp = fields.Boolean("Projects ", implied_group='project_mrp.group_project_mrp')
