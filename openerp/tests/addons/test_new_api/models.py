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

import re

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


from openerp import Model, fields
from openerp import constrains, depends, model, multi, one, scope

class res_partner(Model):
    _inherit = 'res.partner'

    number_of_employees = fields.Integer(compute='default_number_of_employees')
    some_float_field = fields.Float(digits=(10,2))
    some_reference_field = fields.Reference(selection='_references_models')

    name_size = fields.Integer(store=False,
        compute='compute_name_size', search='search_name_size')
    children_count = fields.Integer(compute='compute_children_count', store=True)
    has_sibling = fields.Boolean(compute='compute_has_sibling', store=True)
    family_size = fields.Integer(compute='compute_family_size', store=False)

    @one
    def default_number_of_employees(self):
        self.number_of_employees = 1

    @model
    def _references_models(self):
        return [('res.partner', 'Partner'), ('res.users', 'User')]

    @one
    @depends('name')
    def compute_name_size(self):
        self.name_size = len(self.name or '')

    @model
    def search_name_size(self, operator, value):
        assert operator in ('=', '!=', '<', '<=', '>', '>=', 'in', 'not in')
        assert isinstance(value, (int, long))
        # retrieve all the partners that match with a specific SQL query
        query = """SELECT id FROM "%s" WHERE char_length("name") %s %%s""" % \
                (self._table, operator)
        cr = scope.cr
        cr.execute(query, (value,))
        ids = [t[0] for t in cr.fetchall()]
        return [('id', 'in', ids)]

    @one
    @depends('child_ids')
    def compute_children_count(self):
        self.children_count = len(self.child_ids)

    # depends on function field => cascading recomputations
    @one
    @depends('parent_id.children_count')
    def compute_has_sibling(self):
        self.has_sibling = self.parent_id.children_count >= 2

    @multi
    @depends('child_ids')
    def compute_family_size(self):
        # make sure to trigger dependencies by sorting records in alphabetical order
        self = sum(sorted(self, key=lambda rec: rec.name), self.browse())
        for rec in self:
            rec.family_size = 1 + sum(child.family_size for child in rec.child_ids)

    computed_company = fields.Many2one('res.company', compute='compute_relations', store=False)
    computed_companies = fields.Many2many('res.company', compute='compute_relations', store=False)

    @one
    @depends('company_id')
    def compute_relations(self):
        self.computed_company = self.company_id
        self.computed_companies = self.company_id

    company_name = fields.Char(related='company_id.name', store=False)


email_re = re.compile("^(.*) <(.*)>$")

class field_inverse(Model):
    _name = 'test_new_api.inverse'

    name = fields.Char()
    email = fields.Char()
    full_name = fields.Char(store=False,
                    compute='compute_full_name', inverse='inverse_full_name')

    @one
    @constrains('name', 'email')
    def _check_name_email(self):
        if '@' in (self.name or ''):
            raise ValueError("Name may not contain '@': %r" % self.name)
        if self.email and '@' not in self.email:
            raise ValueError("Email must contain '@': %r" % self.email)

    @one
    @depends('name', 'email')
    def compute_full_name(self):
        self.full_name = "%s <%s>" % (self.name, self.email)

    @one
    def inverse_full_name(self):
        self.name, self.email = email_re.match(self.full_name).groups()


class on_change_test(Model):
    _name = 'test_new_api.on_change'

    name = fields.Char()
    name_size = fields.Integer(compute='compute_name_size', store=False)
    name_utf8_size = fields.Integer(compute='compute_utf8_size', store=False)
    description = fields.Char(compute='compute_description')
    trick = fields.Char(compute='whatever', store=False)


    @one
    @depends('name')
    def compute_name_size(self):
        self.name_size = len(self.name or '')

    @one
    @depends('name')
    def compute_utf8_size(self):
        name = self.name or u''
        self.name_utf8_size = len(name.encode('utf-8'))

    @one
    @depends('name', 'name_size', 'name_utf8_size')
    def compute_description(self):
        if self.name:
            self.description = "%s (%d:%d)" % (
                self.name or '', self.name_size, self.name_utf8_size)
        else:
            self.description = False

    @one
    def whatever(self):
        self.trick = "wheeeeeld.null()eld.null"


class defaults(Model):
    _name = 'test_new_api.defaults'

    name = fields.Char(required=True, compute=fields.default(u'Bob the Builder'))
    description = fields.Char()


class InheritsParent(Model):
    _name = 'test_new_api.inherits_parent'
    name = fields.Char()


class InheritsChild(Model):
    _name = 'test_new_api.inherits_child'
    parent = fields.Many2one('test_new_api.inherits_parent', delegate=True)


class mock_model(Model):
    _name = 'test_new_api.mock_model'