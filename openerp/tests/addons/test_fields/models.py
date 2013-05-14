# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields

class res_partner(osv.Model):
    _inherit = 'res.partner'

    #
    # add related fields to test them
    #
    _columns = {
        # a regular one
        'related_company_partner_id': fields.related(
            'company_id', 'partner_id', type='many2one', obj='res.partner'),
        # a related field with a single field
        'single_related_company_id': fields.related(
            'company_id', type='many2one', obj='res.company'),
        # a related field with a single field that is also a related field!
        'related_related_company_id': fields.related(
            'single_related_company_id', type='many2one', obj='res.company'),
    }


from openerp import api, scope, models, fields

class res_partner(models.Model):
    _inherit = 'res.partner'

    number_of_employees = fields.Integer(compute='default_number_of_employees')
    some_float_field = fields.Float(digits=(10,2))
    some_reference_field = fields.Reference(selection='_references_models')

    name_size = fields.Integer(compute='compute_name_size', store=False)
    children_count = fields.Integer(compute='compute_children_count', store=True)
    has_sibling = fields.Integer(compute='compute_has_sibling', store=True)

    @api.record
    def default_number_of_employees(self):
        self.number_of_employees = 1

    @api.model
    def _references_models(self):
        return [('res.partner', 'Partner'), ('res.users', 'User')]

    @api.recordset
    @api.depends('name')
    def compute_name_size(self):
        for rec in self:
            rec.name_size = len(rec.name)

    # Note: we introduce this weird dependency in order to catch changes on both
    # fields 'child_ids' and 'parent_id'
    @api.record
    @api.depends('child_ids.parent_id')
    def compute_children_count(self):
        self.children_count = len(self.child_ids)

    # depends on function field => cascading recomputations
    @api.record
    @api.depends('parent_id.children_count')
    def compute_has_sibling(self):
        self.has_sibling = self.parent_id.children_count >= 2

