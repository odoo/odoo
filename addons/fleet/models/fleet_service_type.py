# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import fields, models


class FleetServiceType(models.Model):

    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection(selection=[('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')],
                                required=True,
                                help='Choose whether the service refer to contracts, vehicle services or both')
