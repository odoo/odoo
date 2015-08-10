# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class fleet_service_type(osv.Model):
    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'category': fields.selection([('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')], 'Category', required=True, help='Choose wheter the service refer to contracts, vehicle services or both'),
    }
