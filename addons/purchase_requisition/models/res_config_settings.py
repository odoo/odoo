# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    group_purchase_alternatives = fields.Boolean("Purchase Alternatives", implied_group='purchase_requisition.group_purchase_alternatives')
