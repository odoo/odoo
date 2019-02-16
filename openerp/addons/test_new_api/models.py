# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from openerp.exceptions import AccessError

##############################################################################
#
#    OLD API
#
##############################################################################
from openerp.osv import osv, fields


class Alpha(osv.Model):
    _name = 'test_new_api.alpha'
    _columns = {
        'name': fields.char(),
    }

class Bravo(osv.Model):
    _name = 'test_new_api.bravo'
    _columns = {
        'alpha_id': fields.many2one('test_new_api.alpha'),
        # a related field with a non-trivial path
        'alpha_name': fields.related('alpha_id', 'name', type='char'),
        # a related field with a single field
        'related_alpha_id': fields.related('alpha_id', type='many2one', obj='test_new_api.alpha'),
        # a related field with a single field that is also a related field!
        'related_related_alpha_id': fields.related('related_alpha_id', type='many2one', obj='test_new_api.alpha'),
    }


class TestFunctionCounter(osv.Model):
    _name = 'test_old_api.function_counter'

    def _compute_cnt(self, cr, uid, ids, fname, arg, context=None):
        res = {}
        for cnt in self.browse(cr, uid, ids, context=context):
            res[cnt.id] = cnt.access and cnt.cnt + 1 or 0
        return res

    _columns = {
        'access': fields.datetime('Datetime Field'),
        'cnt': fields.function(
            _compute_cnt, type='integer', string='Function Field', store=True),
    }


class TestFunctionNoInfiniteRecursion(osv.Model):
    _name = 'test_old_api.function_noinfiniterecursion'

    def _compute_f1(self, cr, uid, ids, fname, arg, context=None):
        res = {}
        for tf in self.browse(cr, uid, ids, context=context):
            res[tf.id] = 'create' in tf.f0 and 'create' or 'write'
        cntobj = self.pool['test_old_api.function_counter']
        cnt_id = self.pool['ir.model.data'].xmlid_to_res_id(
            cr, uid, 'test_new_api.c1')
        cntobj.write(
            cr, uid, cnt_id, {'access': datetime.datetime.now()},
            context=context)
        return res

    _columns = {
        'f0': fields.char('Char Field'),
        'f1': fields.function(
            _compute_f1, type='char', string='Function Field', store=True),
    }

##############################################################################
#
#    NEW API
#
##############################################################################
from openerp import models, fields, api, _


class Category(models.Model):
    _name = 'test_new_api.category'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_new_api.category')
    root_categ = fields.Many2one(_name, compute='_compute_root_categ')
    display_name = fields.Char(compute='_compute_display_name', inverse='_inverse_display_name')
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_new_api.discussion', 'test_new_api_discussion_category',
                                   'category', 'discussion')

    @api.one
    @api.depends('name', 'parent.display_name')     # this definition is recursive
    def _compute_display_name(self):
        if self.parent:
            self.display_name = self.parent.display_name + ' / ' + self.name
        else:
            self.display_name = self.name

    @api.depends('parent')
    def _compute_root_categ(self):
        for cat in self:
            current = cat
            while current.parent:
                current = current.parent
            cat.root_categ = current

    @api.one
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

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if self.search_count([('id', 'in', self._ids), ('name', '=', 'NOACCESS')]):
            raise AccessError('Sorry')
        return super(Category, self).read(fields=fields, load=load)

class Discussion(models.Model):
    _name = 'test_new_api.discussion'

    name = fields.Char(string='Title', required=True,
        help="General description of what this discussion is about.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_new_api.category',
        'test_new_api_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users')
    messages = fields.One2many('test_new_api.message', 'discussion')
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_new_api.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_new_api.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_new_api.emailmessage', 'discussion')
    important_emails = fields.One2many('test_new_api.emailmessage', 'discussion',
                                       domain=[('important', '=', True)])

    def _domain_very_important(self):
        """Ensure computed O2M domains work as expected."""
        return [("important", "=", True)]

    @api.onchange('moderator')
    def _onchange_moderator(self):
        self.participants |= self.moderator

    @api.onchange('messages')
    def _onchange_messages(self):
        self.message_concat = "\n".join(["%s:%s" % (m.name, m.body) for m in self.messages])


class Message(models.Model):
    _name = 'test_new_api.message'

    discussion = fields.Many2one('test_new_api.discussion', ondelete='cascade')
    body = fields.Text()
    author = fields.Many2one('res.users', default=lambda self: self.env.user)
    name = fields.Char(string='Title', compute='_compute_name', store=True)
    display_name = fields.Char(string='Abstract', compute='_compute_display_name')
    size = fields.Integer(compute='_compute_size', search='_search_size')
    double_size = fields.Integer(compute='_compute_double_size')
    discussion_name = fields.Char(related='discussion.name')
    author_partner = fields.Many2one(
        'res.partner', compute='_compute_author_partner',
        search='_search_author_partner')
    important = fields.Boolean()

    @api.one
    @api.constrains('author', 'discussion')
    def _check_author(self):
        if self.discussion and self.author not in self.discussion.participants:
            raise ValueError(_("Author must be among the discussion participants."))

    @api.one
    @api.depends('author.name', 'discussion.name')
    def _compute_name(self):
        self.name = "[%s] %s" % (self.discussion.name or '', self.author.name or '')

    @api.one
    @api.depends('author.name', 'discussion.name', 'body')
    def _compute_display_name(self):
        stuff = "[%s] %s: %s" % (self.author.name, self.discussion.name or '', self.body or '')
        self.display_name = stuff[:80]

    @api.one
    @api.depends('body')
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

    @api.one
    @api.depends('size')
    def _compute_double_size(self):
        # This illustrates a subtle situation: self.double_size depends on
        # self.size. When size is computed, self.size is assigned, which should
        # normally invalidate self.double_size. However, this may not happen
        # while self.double_size is being computed: the last statement below
        # would fail, because self.double_size would be undefined.
        self.double_size = 0
        size = self.size
        self.double_size = self.double_size + size

    @api.one
    @api.depends('author', 'author.partner_id')
    def _compute_author_partner(self):
        self.author_partner = author.partner_id

    @api.model
    def _search_author_partner(self, operator, value):
        return [('author.partner_id', operator, value)]


class EmailMessage(models.Model):
    _name = 'test_new_api.emailmessage'
    _inherits = {'test_new_api.message': 'message'}

    message = fields.Many2one('test_new_api.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')

class Multi(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_new_api.multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_new_api.multi.line', 'multi')

    @api.onchange('name')
    def _onchange_name(self):
        for line in self.lines:
            line.name = self.name

    @api.onchange('partner')
    def _onchange_partner(self):
        for line in self.lines:
            line.partner = self.partner


class MultiLine(models.Model):
    _name = 'test_new_api.multi.line'

    multi = fields.Many2one('test_new_api.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one('res.partner')


class MixedModel(models.Model):
    _name = 'test_new_api.mixed'

    number = fields.Float(digits=(10, 2), default=3.14)
    date = fields.Date()
    now = fields.Datetime(compute='_compute_now')
    lang = fields.Selection(string='Language', selection='_get_lang')
    reference = fields.Reference(string='Related Document',
        selection='_reference_models')

    @api.one
    def _compute_now(self):
        # this is a non-stored computed field without dependencies
        self.now = fields.Datetime.now()

    @api.model
    def _get_lang(self):
        langs = self.env['res.lang'].search([])
        return [(lang.code, lang.name) for lang in langs]

    @api.model
    def _reference_models(self):
        models = self.env['ir.model'].search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]


class BoolModel(models.Model):
    _name = 'domain.bool'

    bool_true = fields.Boolean('b1', default=True)
    bool_false = fields.Boolean('b2', default=False)
    bool_undefined = fields.Boolean('b3')


class Foo(models.Model):
    _name = 'test_new_api.foo'

    name = fields.Char()
    value1 = fields.Integer()
    value2 = fields.Integer()


class Bar(models.Model):
    _name = 'test_new_api.bar'

    name = fields.Char()
    foo = fields.Many2one('test_new_api.foo', compute='_compute_foo')
    value1 = fields.Integer(related='foo.value1')
    value2 = fields.Integer(related='foo.value2')

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_new_api.foo'].search([('name', '=', bar.name)], limit=1)


class ComputeRecursive(models.Model):
    _name = 'test_new_api.recursive'

    name = fields.Char(required=True)
    parent = fields.Many2one('test_new_api.recursive')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('name', 'parent.display_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent:
                rec.display_name = rec.parent.display_name + " / " + rec.name
            else:
                rec.display_name = rec.name
