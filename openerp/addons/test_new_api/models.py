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


from openerp import Model, Integer, Float, Char, Text, Date, Selection, \
    Reference, Many2one, One2many, Many2many, constrains, onchange, depends, \
    model, one, _


class Category(Model):
    _name = 'test_new_api.category'

    name = Char(required=True)
    parent = Many2one('test_new_api.category')
    display_name = Char(compute='_compute_display_name', inverse='_inverse_display_name')

    @one
    @depends('name', 'parent.display_name')     # this definition is recursive
    def _compute_display_name(self):
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

    name = Char(string='Title', required=True,
        help="General description of what this discussion is about.")
    moderator = Many2one('res.users')
    categories = Many2many('test_new_api.category',
        'test_new_api_discussion_category', 'discussion', 'category')
    participants = Many2many('res.users')
    messages = One2many('test_new_api.message', 'discussion')

    @onchange('moderator')
    def _onchange_moderator(self):
        self.participants |= self.moderator


class Message(Model):
    _name = 'test_new_api.message'

    discussion = Many2one('test_new_api.discussion', ondelete='cascade')
    body = Text()
    author = Many2one('res.users', default=lambda self: self.env.user)
    name = Char(string='Title', compute='_compute_name', store=True)
    display_name = Char(string='Abstract', compute='_compute_display_name')
    size = Integer(compute='_compute_size', search='_search_size')
    double_size = Integer(compute='_compute_double_size')
    discussion_name = Char(related='discussion.name', readonly=True)

    @one
    @constrains('author', 'discussion')
    def _check_author(self):
        if self.discussion and self.author not in self.discussion.participants:
            raise ValueError(_("Author must be among the discussion participants."))

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
        self.env.cr.execute(query, (value,))
        ids = [t[0] for t in self.env.cr.fetchall()]
        return [('id', 'in', ids)]

    @one
    @depends('size')
    def _compute_double_size(self):
        # This illustrates a subtle situation: self.double_size depends on
        # self.size. When size is computed, self.size is assigned, which should
        # normally invalidate self.double_size. However, this may not happen
        # while self.double_size is being computed: the last statement below
        # would fail, because self.double_size would be undefined.
        self.double_size = 0
        size = self.size
        self.double_size = self.double_size + size


class Talk(Model):
    _name = 'test_new_api.talk'

    parent = Many2one('test_new_api.discussion', delegate=True)


class MixedModel(Model):
    _name = 'test_new_api.mixed'

    number = Float(digits=(10, 2), default=3.14)
    date = Date()
    lang = Selection(string='Language', selection='_get_lang')
    reference = Reference(string='Related Document',
        selection='_reference_models')

    @model
    def _get_lang(self):
        langs = self.env['res.lang'].search([])
        return [(lang.code, lang.name) for lang in langs]

    @model
    def _reference_models(self):
        models = self.env['ir.model'].search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]
