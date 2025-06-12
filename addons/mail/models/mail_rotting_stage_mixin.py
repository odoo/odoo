# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class RottingStageMixin(models.AbstractModel):
    _name = 'mail.rotting.stage.mixin'
    _description = 'Mixin for resouurces that can hold rotting resources, inheriting mail.rotting.resource.mixin'

    day_rot = fields.Integer('Days to rot', default=5, help="Day count before resources in this stage become stale. Set to 0 to disable")
