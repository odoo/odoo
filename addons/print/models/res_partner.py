# -*- coding: utf-8 -*-
from openerp import api, fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    has_address = fields.Boolean(string='Is address valid', readonly=True, store=True, compute='_compute_has_address')

    @api.depends('street', 'zip', 'country_id', 'state_id', 'city')
    def _compute_has_address(self):
        for partner in self:
            partner.has_address = bool(partner.street and partner.city and partner.zip and partner.country_id)
