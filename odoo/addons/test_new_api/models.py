# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import pycompat


class Category(models.Model):
    _name = 'test_new_api.category'
    _description = 'Test New API Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_new_api.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
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
        for parent, child in pycompat.izip(categories, categories[1:]):
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
    _description = 'Test New API Discussion'

    name = fields.Char(string='Title', required=True,
        help="General description of what this discussion is about.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_new_api.category',
        'test_new_api_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_new_api.message', 'discussion', copy=True)
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

    @api.onchange('name')
    def _onchange_name(self):
        # test onchange modifying one2many field values
        if self.env.context.get('generate_dummy_message') and self.name == '{generate_dummy_message}':
            # update body of existings messages and emails
            for message in self.messages:
                message.body = 'not last dummy message'
            for message in self.important_messages:
                message.body = 'not last dummy message'
            # add new dummy message
            message_vals = self.messages._add_missing_default_values({'body': 'dummy message', 'important': True})
            self.messages |= self.messages.new(message_vals)
            self.important_messages |= self.messages.new(message_vals)

    @api.onchange('moderator')
    def _onchange_moderator(self):
        self.participants |= self.moderator

    @api.onchange('messages')
    def _onchange_messages(self):
        self.message_concat = "\n".join(["%s:%s" % (m.name, m.body) for m in self.messages])


class Message(models.Model):
    _name = 'test_new_api.message'
    _description = 'Test New API Message'

    discussion = fields.Many2one('test_new_api.discussion', ondelete='cascade')
    body = fields.Text()
    author = fields.Many2one('res.users', default=lambda self: self.env.user)
    name = fields.Char(string='Title', compute='_compute_name', store=True)
    display_name = fields.Char(string='Abstract', compute='_compute_display_name')
    size = fields.Integer(compute='_compute_size', search='_search_size')
    double_size = fields.Integer(compute='_compute_double_size')
    discussion_name = fields.Char(related='discussion.name', string="Discussion Name", readonly=False)
    author_partner = fields.Many2one(
        'res.partner', compute='_compute_author_partner',
        search='_search_author_partner')
    important = fields.Boolean()
    label = fields.Char(translate=True)

    @api.one
    @api.constrains('author', 'discussion')
    def _check_author(self):
        if self.discussion and self.author not in self.discussion.participants:
            raise ValidationError(_("Author must be among the discussion participants."))

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
        self.author_partner = self.author.partner_id

    @api.model
    def _search_author_partner(self, operator, value):
        return [('author.partner_id', operator, value)]


class EmailMessage(models.Model):
    _name = 'test_new_api.emailmessage'
    _description = 'Test New API Email Message'
    _inherits = {'test_new_api.message': 'message'}

    message = fields.Many2one('test_new_api.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')


class Multi(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_new_api.multi'
    _description = 'Test New API Multi'

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
    _description = 'Test New API Multi Line'

    multi = fields.Many2one('test_new_api.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one('res.partner')
    tags = fields.Many2many('test_new_api.multi.tag')


class MultiTag(models.Model):
    _name = 'test_new_api.multi.tag'
    _description = 'Test New API Multi Tag'

    name = fields.Char()


class Edition(models.Model):
    _name = 'test_new_api.creativework.edition'
    _description = 'Test New API Creative Work Edition'

    name = fields.Char()
    res_id = fields.Integer(required=True)
    res_model_id = fields.Many2one('ir.model', required=True)
    res_model = fields.Char(related='res_model_id.model', store=True, readonly=False)


class Book(models.Model):
    _name = 'test_new_api.creativework.book'
    _description = 'Test New API Creative Work Book'

    name = fields.Char()
    editions = fields.One2many(
        'test_new_api.creativework.edition', 'res_id', domain=[('res_model', '=', _name)]
    )


class Movie(models.Model):
    _name = 'test_new_api.creativework.movie'
    _description = 'Test New API Creative Work Movie'

    name = fields.Char()
    editions = fields.One2many(
        'test_new_api.creativework.edition', 'res_id', domain=[('res_model', '=', _name)]
    )


class MixedModel(models.Model):
    _name = 'test_new_api.mixed'
    _description = 'Test New API Mixed'

    number = fields.Float(digits=(10, 2), default=3.14)
    date = fields.Date()
    now = fields.Datetime(compute='_compute_now')
    lang = fields.Selection(string='Language', selection='_get_lang')
    reference = fields.Reference(string='Related Document',
        selection='_reference_models')
    comment1 = fields.Html(sanitize=False)
    comment2 = fields.Html(sanitize_attributes=True, strip_classes=False)
    comment3 = fields.Html(sanitize_attributes=True, strip_classes=True)
    comment4 = fields.Html(sanitize_attributes=True, strip_style=True)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    amount = fields.Monetary()

    @api.one
    def _compute_now(self):
        # this is a non-stored computed field without dependencies
        self.now = fields.Datetime.now()

    @api.model
    def _get_lang(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _reference_models(self):
        models = self.env['ir.model'].sudo().search([('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]


class BoolModel(models.Model):
    _name = 'domain.bool'
    _description = 'Boolean Domain'

    bool_true = fields.Boolean('b1', default=True)
    bool_false = fields.Boolean('b2', default=False)
    bool_undefined = fields.Boolean('b3')


class Foo(models.Model):
    _name = 'test_new_api.foo'
    _description = 'Test New API Foo'

    name = fields.Char()
    value1 = fields.Integer(change_default=True)
    value2 = fields.Integer()


class Bar(models.Model):
    _name = 'test_new_api.bar'
    _description = 'Test New API Bar'

    name = fields.Char()
    foo = fields.Many2one('test_new_api.foo', compute='_compute_foo')
    value1 = fields.Integer(related='foo.value1', readonly=False)
    value2 = fields.Integer(related='foo.value2', readonly=False)

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_new_api.foo'].search([('name', '=', bar.name)], limit=1)


class Related(models.Model):
    _name = 'test_new_api.related'
    _description = 'Test New API Related'

    name = fields.Char()
    # related fields with a single field
    related_name = fields.Char(related='name', string='A related on Name', readonly=False)
    related_related_name = fields.Char(related='related_name', string='A related on a related on Name', readonly=False)

    message = fields.Many2one('test_new_api.message')
    message_name = fields.Text(related="message.body", related_sudo=False, string='Message Body', readonly=False)
    message_currency = fields.Many2one(related="message.author", string='Message Author', readonly=False)

class ComputeProtected(models.Model):
    _name = 'test_new_api.compute.protected'
    _description = 'Test New API Compute Protected'

    foo = fields.Char(default='')
    bar = fields.Char(compute='_compute_bar', store=True)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = record.foo

class ComputeInverse(models.Model):
    _name = 'test_new_api.compute.inverse'
    _description = 'Test New API Compute Inversse'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', inverse='_inverse_bar', store=True)

    @api.depends('foo')
    def _compute_bar(self):
        self._context.get('log', []).append('compute')
        for record in self:
            record.bar = record.foo

    def _inverse_bar(self):
        self._context.get('log', []).append('inverse')
        for record in self:
            record.foo = record.bar


class MultiComputeInverse(models.Model):
    """ Model with the same inverse method for several fields. """
    _name = 'test_new_api.multi_compute_inverse'
    _description = 'Test New API Multi Compute Inverse'

    foo = fields.Char(default='', required=True)
    bar1 = fields.Char(compute='_compute_bars', inverse='_inverse_bar1', store=True)
    bar2 = fields.Char(compute='_compute_bars', inverse='_inverse_bar23', store=True)
    bar3 = fields.Char(compute='_compute_bars', inverse='_inverse_bar23', store=True)

    @api.depends('foo')
    def _compute_bars(self):
        self._context.get('log', []).append('compute')
        for record in self:
            substrs = record.foo.split('/') + ['', '', '']
            record.bar1, record.bar2, record.bar3 = substrs[:3]

    def _inverse_bar1(self):
        self._context.get('log', []).append('inverse1')
        for record in self:
            record.write({'foo': '/'.join([record.bar1, record.bar2, record.bar3])})

    def _inverse_bar23(self):
        self._context.get('log', []).append('inverse23')
        for record in self:
            record.write({'foo': '/'.join([record.bar1, record.bar2, record.bar3])})


class CompanyDependent(models.Model):
    _name = 'test_new_api.company'
    _description = 'Test New API Company'

    foo = fields.Char(company_dependent=True)
    date = fields.Date(company_dependent=True)
    moment = fields.Datetime(company_dependent=True)
    tag_id = fields.Many2one('test_new_api.multi.tag', company_dependent=True)


class CompanyDependentAttribute(models.Model):
    _name = 'test_new_api.company.attr'
    _description = 'Test New API Company Attribute'

    company = fields.Many2one('test_new_api.company')
    quantity = fields.Integer()
    bar = fields.Char(compute='_compute_bar', store=True)

    @api.depends('quantity', 'company.foo')
    def _compute_bar(self):
        for record in self:
            record.bar = (record.company.foo or '') * record.quantity


class ComputeRecursive(models.Model):
    _name = 'test_new_api.recursive'
    _description = 'Test New API Recursive'

    name = fields.Char(required=True)
    parent = fields.Many2one('test_new_api.recursive', ondelete='cascade')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('name', 'parent.display_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent:
                rec.display_name = rec.parent.display_name + " / " + rec.name
            else:
                rec.display_name = rec.name


class ComputeCascade(models.Model):
    _name = 'test_new_api.cascade'
    _description = 'Test New API Cascade'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar')               # depends on foo
    baz = fields.Char(compute='_compute_baz', store=True)   # depends on bar

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = "[%s]" % (record.foo or "")

    @api.depends('bar')
    def _compute_baz(self):
        for record in self:
            record.baz = "<%s>" % (record.bar or "")


class BinarySvg(models.Model):
    _name = 'test_new_api.binary_svg'
    _description = 'Test SVG upload'

    name = fields.Char(required=True)
    image_attachment = fields.Binary(attachment=True)
    image_wo_attachment = fields.Binary(attachment=False)


class MonetaryBase(models.Model):
    _name = 'test_new_api.monetary_base'
    _description = 'Monetary Base'

    base_currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary(currency_field='base_currency_id')


class MonetaryRelated(models.Model):
    _name = 'test_new_api.monetary_related'
    _description = 'Monetary Related'

    monetary_id = fields.Many2one('test_new_api.monetary_base')
    currency_id = fields.Many2one('res.currency', related='monetary_id.base_currency_id')
    amount = fields.Monetary(related='monetary_id.amount')


class MonetaryCustom(models.Model):
    _name = 'test_new_api.monetary_custom'
    _description = 'Monetary Related Custom'

    monetary_id = fields.Many2one('test_new_api.monetary_base')
    x_currency_id = fields.Many2one('res.currency', related='monetary_id.base_currency_id')
    x_amount = fields.Monetary(related='monetary_id.amount')


class MonetaryInherits(models.Model):
    _name = 'test_new_api.monetary_inherits'
    _description = 'Monetary Inherits'
    _inherits = {'test_new_api.monetary_base': 'monetary_id'}

    monetary_id = fields.Many2one('test_new_api.monetary_base', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency')


class FieldWithCaps(models.Model):
    _name = 'test_new_api.field_with_caps'
    _description = 'Model with field defined with capital letters'

    pArTneR_321_id = fields.Many2one('res.partner')
