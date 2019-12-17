# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Opp. Lost Reason'

    name = fields.Char('Description', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
