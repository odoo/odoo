# -*- coding: utf-8 -*-

from openerp import fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    claim_ids = fields.One2many('crm.claim', 'partner_id', string="Claims")
