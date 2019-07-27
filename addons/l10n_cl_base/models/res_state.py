# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
# Copyright (c) 2012 Cubic ERP - Teradata SAC. (http://cubicerp.com).
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from odoo import models, fields, api


class ResState(models.Model):
    _name = 'res.country.state'
    _inherit = 'res.country.state'

    # code = fields.Char(
    #     'State Code', size=32, help='The state code.\n', required=True)
    # complete_name = fields.Char(
    #     string='Complete Name')
    parent_id = fields.Many2one(
        'res.country.state', 'Parent State', index=True,
        domain="[('type', '=', 'view'), ('id', '!=', id)]")
    child_ids = fields.One2many(
        'res.country.state', 'parent_id', string='Child States')
    type = fields.Selection(
        [('view', 'View'), ('normal', 'Normal')], 'Type', default='normal')
