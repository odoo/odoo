# -*- coding: utf-8 -*-
from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    mp_distributor = fields.Boolean('Marketplace Distributor', default=False)
    mp_entity_id = fields.Integer('Distributor ID')
