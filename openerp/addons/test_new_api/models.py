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


from openerp import Model, fields
from openerp import constrains, depends, model, multi, one


class Category(Model):
    _name = 'test_new_api.category'

    name            = fields.Char(required=True)
    parent          = fields.Many2one('test_new_api.category')
    display_name    = fields.Char(store=False, readonly=True,
                            compute='_compute_display_name',
                            inverse='_inverse_display_name')

    @one
    @depends('name', 'parent')
    def _compute_display_name(self):
        # this definition is recursive
        if self.parent:
            self.display_name = self.parent.display_name + ' / ' + self.name
        else:
            self.display_name = self.name

    @one
    def _inverse_display_name(self):
        names = self.display_name.split('/')
        # determine sequence of categories
        categories = []
        for name in names[:-1]:
            category = self.search([('name', 'ilike', name.strip())])
            categories.append(category[0])
        categories.append(self)
        # assign parents following sequence
        for parent, child in zip(categories, categories[1:]):
            if parent and child:
                child.parent = parent
        # assign name of last category, and reassign display_name (to normalize it)
        self.name = names[-1].strip()


class Discussion(Model):
    _name = 'test_new_api.discussion'

    name            = fields.Char(string='Title', required=True)
    categories      = fields.Many2many('test_new_api.category',
                            'test_new_api_discussion_category', 'discussion', 'category')
    participants    = fields.Many2many('res.users')
    messages        = fields.One2many('test_new_api.message', 'discussion')


class Message(Model):
    _name = 'test_new_api.message'

    discussion      = fields.Many2one('test_new_api.discussion',
                            ondelete='cascade')
    body            = fields.Text()
    author          = fields.Many2one('res.users', compute='_default_author')
    name            = fields.Char(string='Title', store=True, readonly=True,
                            compute='_compute_name')
    display_name    = fields.Char(string='Abstract', store=False, readonly=True,
                            compute='_compute_display_name')
    size            = fields.Integer(store=False, readonly=True,
                            compute='_compute_size', search='_search_size')
    discussion_name = fields.Char(related='discussion.name', store=False)

    @one
    def _default_author(self):
        self.author = self._scope.user

    @one
    @constrains('author', 'discussion')
    def _check_author(self):
        if self.discussion and self.author not in self.discussion.participants:
            raise ValueError("Author must be among the discussion participants.")

    @one
    @depends('author.name', 'discussion.name')
    def _compute_name(self):
        self.name = "[%s] %s" % (self.discussion.name or '', self.author.name)

    @one
    @depends('author.name', 'discussion.name', 'body')
    def _compute_display_name(self):
        stuff = "[%s] %s: %s" % (self.author.name, self.discussion.name or '', self.body or '')
        self.display_name = stuff[:80]

    @one
    @depends('body')
    def _compute_size(self):
        self.size = len(self.body or '')

    def _search_size(self, operator, value):
        if operator not in ('=', '!=', '<', '<=', '>', '>=', 'in', 'not in'):
            return []
        # retrieve all the messages that match with a specific SQL query
        query = """SELECT id FROM "%s" WHERE char_length("body") %s %%s""" % \
                (self._table, operator)
        self._scope.cr.execute(query, (value,))
        ids = [t[0] for t in self._scope.cr.fetchall()]
        return [('id', 'in', ids)]


class Talk(Model):
    _name = 'test_new_api.talk'

    parent = fields.Many2one('test_new_api.discussion', delegate=True)


class MixedModel(Model):
    _name = 'test_new_api.mixed'

    number      = fields.Float(digits=(10, 2))
    date        = fields.Date()
    lang        = fields.Selection(string='Language', selection='_get_lang')
    reference   = fields.Reference(string='Related Document', selection='_reference_models')

    @model
    def _get_lang(self):
        langs = self._scope['res.lang'].search([])
        return [(lang.code, lang.name) for lang in langs]

    @model
    def _reference_models(self):
        models = self._scope['ir.model'].search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]
