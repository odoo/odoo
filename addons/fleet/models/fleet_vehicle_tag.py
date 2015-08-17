# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class fleet_vehicle_tag(osv.Model):
    _name = 'fleet.vehicle.tag'
    _columns = {
        'name': fields.char('Name', required=True),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
