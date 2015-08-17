# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import time
import datetime
from openerp import tools
from openerp.exceptions import UserError
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta


class fleet_vehicle_state(osv.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'
    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', help="Used to order the note stages")
    }
    _sql_constraints = [('fleet_state_name_unique','unique(name)', 'State name already exists')]
