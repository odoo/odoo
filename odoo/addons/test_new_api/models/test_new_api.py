# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger('precompute_setter')

from odoo import models, fields, api, _, Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.translate import html_translate


class Category(models.Model):
    _name = 'test_new_api.category'
    _description = 'Test New API Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_new_api.category', ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one(_name, compute='_compute_root_categ')
    display_name = fields.Char(compute='_compute_display_name', recursive=True,
                               inverse='_inverse_display_name')
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_new_api.discussion', 'test_new_api_discussion_category',
                                   'category', 'discussion')

    _sql_constraints = [
        ('positive_color', 'CHECK(color >= 0)', 'The color code must be positive !')
    ]

    @api.depends('name', 'parent.display_name')     # this definition is recursive
    def _compute_display_name(self):
        for cat in self:
            if cat.parent:
                cat.display_name = cat.parent.display_name + ' / ' + cat.name
            else:
                cat.display_name = cat.name

    @api.depends('parent')
    def _compute_root_categ(self):
        for cat in self:
            current = cat
            while current.parent:
                current = current.parent
            cat.root_categ = current

    @api.depends('parent_path')
    def _compute_depth(self):
        for cat in self:
            cat.depth = cat.parent_path.count('/') - 1

    def _inverse_display_name(self):
        for cat in self:
            names = cat.display_name.split('/')
            # determine sequence of categories
            categories = []
            for name in names[:-1]:
                category = self.search([('name', 'ilike', name.strip())])
                categories.append(category[0])
            categories.append(cat)
            # assign parents following sequence
            for parent, child in zip(categories, categories[1:]):
                if parent and child:
                    child.parent = parent
            # assign name of last category, and reassign display_name (to normalize it)
            cat.name = names[-1].strip()

    def _read(self, fields):
        # DLE P45: `test_31_prefetch`,
        # with self.assertRaises(AccessError):
        #     cat1.name
        if self.search_count([('id', 'in', self._ids), ('name', '=', 'NOACCESS')]):
            raise AccessError('Sorry')
        return super(Category, self)._read(fields)


class Discussion(models.Model):
    _name = 'test_new_api.discussion'
    _description = 'Test New API Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
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

    history = fields.Json('History', default={'delete_messages': []})
    attributes_definition = fields.PropertiesDefinition('Message Properties')  # see message@attributes

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
    priority = fields.Integer()

    attributes = fields.Properties(
        string='Properties',
        definition='discussion.attributes_definition',
    )

    @api.constrains('author', 'discussion')
    def _check_author(self):
        for message in self.with_context(active_test=False):
            if message.discussion and message.author not in message.discussion.participants:
                raise ValidationError(_("Author must be among the discussion participants."))

    @api.depends('author.name', 'discussion.name')
    def _compute_name(self):
        for message in self:
            message.name = self._context.get('compute_name',
                "[%s] %s" % (message.discussion.name or '', message.author.name or ''))

    @api.constrains('name')
    def _check_name(self):
        # dummy constraint to check on computed field
        for message in self:
            if message.name.startswith("[X]"):
                raise ValidationError("No way!")

    @api.depends('author.name', 'discussion.name', 'body')
    def _compute_display_name(self):
        for message in self:
            stuff = "[%s] %s: %s" % (message.author.name, message.discussion.name or '', message.body or '')
            message.display_name = stuff[:80]

    @api.depends('body')
    def _compute_size(self):
        for message in self:
            message.size = len(message.body or '')

    def _search_size(self, operator, value):
        if operator not in ('=', '!=', '<', '<=', '>', '>=', 'in', 'not in'):
            return []
        # retrieve all the messages that match with a specific SQL query
        self.flush_model(['body'])
        query = """SELECT id FROM "%s" WHERE char_length("body") %s %%s""" % \
                (self._table, operator)
        self.env.cr.execute(query, (value,))
        ids = [t[0] for t in self.env.cr.fetchall()]
        # return domain with an implicit AND
        return [('id', 'in', ids), (1, '=', 1)]

    @api.depends('size')
    def _compute_double_size(self):
        for message in self:
            # This illustrates a subtle situation: message.double_size depends
            # on message.size. When the latter is computed, message.size is
            # assigned, which would normally invalidate message.double_size.
            # However, this may not happen while message.double_size is being
            # computed: the last statement below would fail, because
            # message.double_size would be undefined.
            message.double_size = 0
            size = message.size
            message.double_size = message.double_size + size

    @api.depends('author', 'author.partner_id')
    def _compute_author_partner(self):
        for message in self:
            message.author_partner = message.author.partner_id

    @api.model
    def _search_author_partner(self, operator, value):
        return [('author.partner_id', operator, value)]

    def write(self, vals):
        if 'priority' in vals:
            vals['priority'] = 5
        return super().write(vals)


class EmailMessage(models.Model):
    _name = 'test_new_api.emailmessage'
    _description = 'Test New API Email Message'
    _inherits = {'test_new_api.message': 'message'}

    message = fields.Many2one('test_new_api.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')


class DiscussionPartner(models.Model):
    """
    Simplified model for partners. Having a specific model avoids all the
    overrides from other modules that may change which fields are being read,
    how many queries it takes to use that model, etc.
    """
    _name = 'test_new_api.partner'
    _description = 'Discussion Partner'

    name = fields.Char(string='Name')


class Multi(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_new_api.multi'
    _description = 'Test New API Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_new_api.multi.line', 'multi')
    partners = fields.One2many(related='partner.child_ids')
    tags = fields.Many2many('test_new_api.multi.tag', domain=[('name', 'ilike', 'a')])

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
    partner = fields.Many2one(related='multi.partner', store=True)
    tags = fields.Many2many('test_new_api.multi.tag')


class MultiLine2(models.Model):
    _name = 'test_new_api.multi.line2'
    _inherit = 'test_new_api.multi.line'
    _description = 'Test New API Multi Line 2'


class MultiTag(models.Model):
    _name = 'test_new_api.multi.tag'
    _description = 'Test New API Multi Tag'

    name = fields.Char()


class Edition(models.Model):
    _name = 'test_new_api.creativework.edition'
    _description = 'Test New API Creative Work Edition'

    name = fields.Char()
    res_id = fields.Integer(required=True)
    res_model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
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
    number2 = fields.Float(digits='New API Precision')
    date = fields.Date()
    moment = fields.Datetime()
    now = fields.Datetime(compute='_compute_now')
    lang = fields.Selection(string='Language', selection='_get_lang')
    reference = fields.Reference(string='Related Document',
        selection='_reference_models')
    comment1 = fields.Html(sanitize=False)
    comment2 = fields.Html(sanitize_attributes=True, strip_classes=False)
    comment3 = fields.Html(sanitize_attributes=True, strip_classes=True)
    comment4 = fields.Html(sanitize_attributes=True, strip_style=True)
    comment5 = fields.Html(sanitize_overridable=True, sanitize_attributes=False)

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    amount = fields.Monetary()

    def _compute_now(self):
        # this is a non-stored computed field without dependencies
        for message in self:
            message.now = fields.Datetime.now()

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
    text = fields.Char(trim=False)


class Bar(models.Model):
    _name = 'test_new_api.bar'
    _description = 'Test New API Bar'

    name = fields.Char()
    foo = fields.Many2one('test_new_api.foo', compute='_compute_foo', search='_search_foo')
    value1 = fields.Integer(related='foo.value1', readonly=False)
    value2 = fields.Integer(related='foo.value2', readonly=False)
    text1 = fields.Char('Text1', related='foo.text', readonly=False)
    text2 = fields.Char('Text2', related='foo.text', readonly=False, trim=True)

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_new_api.foo'].search([('name', '=', bar.name)], limit=1)

    def _search_foo(self, operator, value):
        assert operator == 'in'
        records = self.env['test_new_api.foo'].browse(value)
        return [('name', 'in', records.mapped('name'))]


class Related(models.Model):
    _name = 'test_new_api.related'
    _description = 'Test New API Related'

    name = fields.Char()
    # related fields with a single field
    related_name = fields.Char(related='name', string='A related on Name', readonly=False)
    related_related_name = fields.Char(related='related_name', string='A related on a related on Name', readonly=False)

    message = fields.Many2one('test_new_api.message')
    message_name = fields.Text(related="message.body", related_sudo=False, string='Message Body')
    message_currency = fields.Many2one(related="message.author", string='Message Author')


class ComputeReadonly(models.Model):
    _name = 'test_new_api.compute.readonly'
    _description = 'Model with a computed readonly field'

    foo = fields.Char(default='')
    bar = fields.Char(compute='_compute_bar', store=True)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = record.foo


class ComputeInverse(models.Model):
    _name = 'test_new_api.compute.inverse'
    _description = 'Model with a computed inversed field'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', inverse='_inverse_bar', store=True)
    baz = fields.Char()

    @api.depends('foo')
    def _compute_bar(self):
        self._context.get('log', []).append('compute')
        for record in self:
            record.bar = record.foo

    def _inverse_bar(self):
        self._context.get('log', []).append('inverse')
        for record in self:
            record.foo = record.bar

    @api.constrains('bar', 'baz')
    def _check_constraint(self):
        if self._context.get('log_constraint'):
            self._context.get('log', []).append('constraint')


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


class Move(models.Model):
    _name = 'test_new_api.move'
    _description = 'Move'

    line_ids = fields.One2many('test_new_api.move_line', 'move_id', domain=[('visible', '=', True)])
    quantity = fields.Integer(compute='_compute_quantity', store=True)
    tag_id = fields.Many2one('test_new_api.multi.tag')
    tag_name = fields.Char(related='tag_id.name')
    tag_repeat = fields.Integer()
    tag_string = fields.Char(compute='_compute_tag_string')

    # This field can fool the ORM during onchanges!  When editing a payment
    # record, modified fields are assigned to the parent record.  When
    # determining the dependent records, the ORM looks for the payments related
    # to this record by the field `move_id`.  As this field is an inverse of
    # `move_id`, it uses it.  If that field was not initialized properly, the
    # ORM determines its value to be... empty (instead of the payment record.)
    payment_ids = fields.One2many('test_new_api.payment', 'move_id')

    @api.depends('line_ids.quantity')
    def _compute_quantity(self):
        for record in self:
            record.quantity = sum(line.quantity for line in record.line_ids)

    @api.depends('tag_name', 'tag_repeat')
    def _compute_tag_string(self):
        for record in self:
            record.tag_string = (record.tag_name or "") * record.tag_repeat


class MoveLine(models.Model):
    _name = 'test_new_api.move_line'
    _description = 'Move Line'

    move_id = fields.Many2one('test_new_api.move', required=True, ondelete='cascade')
    visible = fields.Boolean(default=True)
    quantity = fields.Integer()


class Payment(models.Model):
    _name = 'test_new_api.payment'
    _description = 'Payment inherits from Move'
    _inherits = {'test_new_api.move': 'move_id'}

    move_id = fields.Many2one('test_new_api.move', required=True, ondelete='cascade')


class Order(models.Model):
    _name = _description = 'test_new_api.order'

    line_ids = fields.One2many('test_new_api.order.line', 'order_id')


class OrderLine(models.Model):
    _name = _description = 'test_new_api.order.line'

    order_id = fields.Many2one('test_new_api.order', required=True, ondelete='cascade')
    product = fields.Char()
    reward = fields.Boolean()

    def unlink(self):
        # also delete associated reward lines
        reward_lines = [
            other_line
            for line in self
            if not line.reward
            for other_line in line.order_id.line_ids
            if other_line.reward and other_line.product == line.product
        ]
        self = self.union(*reward_lines)
        return super().unlink()


class CompanyDependent(models.Model):
    _name = 'test_new_api.company'
    _description = 'Test New API Company'

    foo = fields.Char(company_dependent=True)
    date = fields.Date(company_dependent=True)
    moment = fields.Datetime(company_dependent=True)
    tag_id = fields.Many2one('test_new_api.multi.tag', company_dependent=True)
    truth = fields.Boolean(company_dependent=True)
    count = fields.Integer(company_dependent=True)
    phi = fields.Float(company_dependent=True, digits=(2, 5))


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
    full_name = fields.Char(compute='_compute_full_name', recursive=True)
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True)

    @api.depends('name', 'parent.full_name')
    def _compute_full_name(self):
        for rec in self:
            if rec.parent:
                rec.full_name = rec.parent.full_name + " / " + rec.name
            else:
                rec.full_name = rec.name

    @api.depends('name', 'parent.display_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent:
                rec.display_name = rec.parent.display_name + " / " + rec.name
            else:
                rec.display_name = rec.name


class ComputeRecursiveTree(models.Model):
    _name = 'test_new_api.recursive.tree'
    _description = 'Test New API Recursive with one2many field'

    name = fields.Char(required=True)
    parent_id = fields.Many2one('test_new_api.recursive.tree', ondelete='cascade')
    children_ids = fields.One2many('test_new_api.recursive.tree', 'parent_id')
    display_name = fields.Char(compute='_compute_display_name', recursive=True, store=True)

    @api.depends('name', 'children_ids.display_name')
    def _compute_display_name(self):
        for rec in self:
            children_names = rec.mapped('children_ids.display_name')
            rec.display_name = '%s(%s)' % (rec.name, ', '.join(children_names))


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


class ComputeReadWrite(models.Model):
    _name = 'test_new_api.compute.readwrite'
    _description = 'Model with a computed non-readonly field'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', store=True, readonly=False)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = record.foo


class ComputeOnchange(models.Model):
    _name = 'test_new_api.compute.onchange'
    _description = "Compute method as an onchange"

    active = fields.Boolean()
    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', store=True)
    baz = fields.Char(compute='_compute_baz', store=True, readonly=False)
    count = fields.Integer(default=0)
    line_ids = fields.One2many(
        'test_new_api.compute.onchange.line', 'record_id',
        compute='_compute_line_ids', store=True, readonly=False
    )
    tag_ids = fields.Many2many(
        'test_new_api.multi.tag',
        compute='_compute_tag_ids', store=True, readonly=False,
    )

    @api.onchange('foo')
    def _onchange_foo(self):
        self.count += 1

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = (record.foo or "") + "r"

    @api.depends('active', 'foo')
    def _compute_baz(self):
        for record in self:
            if record.active:
                record.baz = (record.foo or "") + "z"

    @api.depends('foo')
    def _compute_line_ids(self):
        for record in self:
            if not record.foo:
                continue
            if any(line.foo == record.foo for line in record.line_ids):
                continue
            # add a line with the same value as 'foo'
            record.line_ids = [Command.create({'foo': record.foo})]

    @api.depends('foo')
    def _compute_tag_ids(self):
        Tag = self.env['test_new_api.multi.tag']
        for record in self:
            if record.foo:
                record.tag_ids = Tag.search([('name', '=', record.foo)])

    def copy(self, default=None):
        default = dict(default or {}, foo="%s (copy)" % (self.foo or ""))
        return super().copy(default)


class ComputeOnchangeLine(models.Model):
    _name = 'test_new_api.compute.onchange.line'
    _description = "Line-like model for test_new_api.compute.onchange"

    record_id = fields.Many2one('test_new_api.compute.onchange', ondelete='cascade')
    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar')

    @api.depends('foo')
    def _compute_bar(self):
        for line in self:
            line.bar = (line.foo or "") + "r"


class ComputeDynamicDepends(models.Model):
    _name = 'test_new_api.compute.dynamic.depends'
    _description = "Computed field with dynamic dependencies"

    name1 = fields.Char()
    name2 = fields.Char()
    name3 = fields.Char()
    full_name = fields.Char(compute='_compute_full_name')

    def _get_full_name_fields(self):
        # the fields to use are stored in a config parameter
        depends = self.env['ir.config_parameter'].get_param('test_new_api.full_name', '')
        return depends.split(',') if depends else []

    @api.depends(lambda self: self._get_full_name_fields())
    def _compute_full_name(self):
        fnames = self._get_full_name_fields()
        for record in self:
            record.full_name = ", ".join(filter(None, (record[fname] for fname in fnames)))


class ComputeUnassigned(models.Model):
    _name = 'test_new_api.compute.unassigned'
    _description = "Model with computed fields left unassigned"

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar')
    bare = fields.Char(compute='_compute_bare', readonly=False)
    bars = fields.Char(compute='_compute_bars', store=True)
    bares = fields.Char(compute='_compute_bares', readonly=False, store=True)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            if record.foo == "assign":
                record.bar = record.foo

    @api.depends('foo')
    def _compute_bare(self):
        for record in self:
            if record.foo == "assign":
                record.bare = record.foo

    @api.depends('foo')
    def _compute_bars(self):
        for record in self:
            if record.foo == "assign":
                record.bars = record.foo

    @api.depends('foo')
    def _compute_bares(self):
        for record in self:
            if record.foo == "assign":
                record.bares = record.foo


class ComputeOne2many(models.Model):
    _name = 'test_new_api.one2many'
    _description = "A computed editable one2many field with a domain"

    name = fields.Char()
    line_ids = fields.One2many(
        'test_new_api.one2many.line', 'container_id',
        compute='_compute_line_ids', store=True, readonly=False,
        domain=[('count', '>', 0)],
    )

    @api.depends('name')
    def _compute_line_ids(self):
        # increment counter of line with the same name, or create a new line
        for record in self:
            if not record.name:
                continue
            for line in record.line_ids:
                if line.name == record.name:
                    line.count += 1
                    break
            else:
                record.line_ids = [(0, 0, {'name': record.name})]


class ComputeOne2manyLine(models.Model):
    _name = 'test_new_api.one2many.line'
    _description = "Line of a computed one2many"

    name = fields.Char()
    count = fields.Integer(default=1)
    container_id = fields.Many2one('test_new_api.one2many', required=True)


class ModelBinary(models.Model):
    _name = 'test_new_api.model_binary'
    _description = 'Test Image field'

    binary = fields.Binary()
    binary_related_store = fields.Binary("Binary Related Store", related='binary', store=True, readonly=False)
    binary_related_no_store = fields.Binary("Binary Related No Store", related='binary', store=False, readonly=False)
    binary_computed = fields.Binary(compute='_compute_binary')

    @api.depends('binary')
    def _compute_binary(self):
        # arbitrary value: 'bin_size' must have no effect
        for record in self:
            record.binary_computed = [(record.id, bool(record.binary))]


class ModelImage(models.Model):
    _name = 'test_new_api.model_image'
    _description = 'Test Image field'

    name = fields.Char(required=True)

    image = fields.Image()
    image_512 = fields.Image("Image 512", related='image', max_width=512, max_height=512, store=True, readonly=False)
    image_256 = fields.Image("Image 256", related='image', max_width=256, max_height=256, store=False, readonly=False)
    image_128 = fields.Image("Image 128", max_width=128, max_height=128)


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
    total = fields.Monetary()


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


class MonetaryOrder(models.Model):
    _name = 'test_new_api.monetary_order'
    _description = 'Sales Order'

    currency_id = fields.Many2one('res.currency')
    line_ids = fields.One2many('test_new_api.monetary_order_line', 'order_id')
    total = fields.Monetary(compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for record in self:
            record.total = sum(line.subtotal for line in record.line_ids)


class MonetaryOrderLine(models.Model):
    _name = 'test_new_api.monetary_order_line'
    _description = 'Sales Order Line'

    order_id = fields.Many2one('test_new_api.monetary_order', required=True, ondelete='cascade')
    subtotal = fields.Float(digits=(10, 2))


class FieldWithCaps(models.Model):
    _name = 'test_new_api.field_with_caps'
    _description = 'Model with field defined with capital letters'

    pArTneR_321_id = fields.Many2one('res.partner')


class Selection(models.Model):
    _name = 'test_new_api.selection'
    _description = "Selection"

    state = fields.Selection([('foo', 'Foo'), ('bar', 'Bar')])
    other = fields.Selection([('foo', 'Foo'), ('bar', 'Bar')])


class RequiredM2O(models.Model):
    _name = 'test_new_api.req_m2o'
    _description = 'Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='cascade')
    bar = fields.Many2one('res.country', required=True)


class RequiredM2OTransient(models.TransientModel):
    _name = 'test_new_api.req_m2o_transient'
    _description = 'Transient Model with Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='restrict')
    bar = fields.Many2one('res.country', required=True)


class Attachment(models.Model):
    _name = 'test_new_api.attachment'
    _description = 'Attachment'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    name = fields.Char(compute='_compute_name', compute_sudo=True, store=True)

    @api.depends('res_model', 'res_id')
    def _compute_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).display_name

    # DLE P55: `test_cache_invalidation`
    def modified(self, fnames, *args, **kwargs):
        if not self:
            return
        comodel = self.env[self.res_model]
        if 'res_id' in fnames and 'attachment_ids' in comodel:
            record = comodel.browse(self.res_id)
            record.invalidate_recordset(['attachment_ids'])
            record.modified(['attachment_ids'])
        return super(Attachment, self).modified(fnames, *args, **kwargs)


class AttachmentHost(models.Model):
    _name = 'test_new_api.attachment.host'
    _description = 'Attachment Host'

    attachment_ids = fields.One2many(
        'test_new_api.attachment', 'res_id', auto_join=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )

class DecimalPrecisionTestModel(models.Model):
    _name = 'decimal.precision.test'
    _description = 'Decimal Precision Test'

    float = fields.Float()
    float_2 = fields.Float(digits=(16, 2))
    float_4 = fields.Float(digits=(16, 4))


class ModelA(models.Model):
    _name = 'test_new_api.model_a'
    _description = 'Model A'

    name = fields.Char()
    a_restricted_b_ids = fields.Many2many('test_new_api.model_b', relation='rel_model_a_model_b_1')
    b_restricted_b_ids = fields.Many2many('test_new_api.model_b', relation='rel_model_a_model_b_2', ondelete='restrict')


class ModelB(models.Model):
    _name = 'test_new_api.model_b'
    _description = 'Model B'

    name = fields.Char()
    a_restricted_a_ids = fields.Many2many('test_new_api.model_a', relation='rel_model_a_model_b_1', ondelete='restrict')
    b_restricted_a_ids = fields.Many2many('test_new_api.model_a', relation='rel_model_a_model_b_2')


class ModelParent(models.Model):
    _name = 'test_new_api.model_parent'
    _description = 'Model Multicompany parent'

    name = fields.Char()
    company_id = fields.Many2one('res.company', required=True)


class ModelChild(models.Model):
    _name = 'test_new_api.model_child'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company', required=True)
    parent_id = fields.Many2one('test_new_api.model_parent', check_company=True)


class ModelChildNoCheck(models.Model):
    _name = 'test_new_api.model_child_nocheck'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company', required=True)
    parent_id = fields.Many2one('test_new_api.model_parent', check_company=False)


class ModelPrivateAddressOnchange(models.Model):
    _name = 'test_new_api.model_private_address_onchange'
    _description = 'Model Private Address Onchange'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company', required=True)
    address_id = fields.Many2one('res.partner', check_company=True)

    @api.onchange('name')
    def _onchange_name(self):
        if self.name and not self.address_id:
            self.address_id = self.env['res.partner'].sudo().create({
                'name': self.name,
                'type': 'private',
            })

# model with explicit and stored field 'display_name'
class Display(models.Model):
    _name = 'test_new_api.display'
    _description = 'Model that overrides display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    def _compute_display_name(self):
        for record in self:
            record.display_name = 'My id is %s' % (record.id)


# abstract model with automatic and non-stored field 'display_name'
class Mixin(models.AbstractModel):
    _name = 'test_new_api.mixin'
    _description = 'Dummy mixin model'


# in this model extension, the field 'display_name' should not be inherited from
# 'test_new_api.mixin'
class ExtendedDisplay(models.Model):
    _name = 'test_new_api.display'
    _inherit = ['test_new_api.mixin', 'test_new_api.display']


class ModelActiveField(models.Model):
    _name = 'test_new_api.model_active_field'
    _description = 'A model with active field'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_new_api.model_active_field')
    children_ids = fields.One2many('test_new_api.model_active_field', 'parent_id')
    all_children_ids = fields.One2many('test_new_api.model_active_field', 'parent_id',
                                       context={'active_test': False})
    active_children_ids = fields.One2many('test_new_api.model_active_field', 'parent_id',
                                          context={'active_test': True})
    parent_active = fields.Boolean(string='Active Parent', related='parent_id.active', store=True)


class ModelMany2oneReference(models.Model):
    _name = 'test_new_api.model_many2one_reference'
    _description = 'dummy m2oref model'

    res_model = fields.Char('Resource Model')
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model')


class InverseM2oRef(models.Model):
    _name = 'test_new_api.inverse_m2o_ref'
    _description = 'dummy m2oref inverse model'

    model_ids = fields.One2many('test_new_api.model_many2one_reference', 'res_id', string="Models")
    model_ids_count = fields.Integer("Count", compute='_compute_model_ids_count')

    @api.depends('model_ids')
    def _compute_model_ids_count(self):
        for rec in self:
            rec.model_ids_count = len(rec.model_ids)


class ModelChildM2o(models.Model):
    _name = 'test_new_api.model_child_m2o'
    _description = 'dummy model with override write and ValidationError'

    name = fields.Char('Name')
    parent_id = fields.Many2one('test_new_api.model_parent_m2o', ondelete='cascade')
    size1 = fields.Integer(compute='_compute_sizes', store=True)
    size2 = fields.Integer(compute='_compute_sizes', store=True)
    cost = fields.Integer(compute='_compute_cost', store=True, readonly=False)

    @api.depends('parent_id.name')
    def _compute_sizes(self):
        for record in self:
            record.size1 = len(record.parent_id.name)
            record.size2 = len(record.parent_id.name)

    @api.depends('name')
    def _compute_cost(self):
        for record in self:
            record.cost = len(record.name)

    def write(self, vals):
        res = super(ModelChildM2o, self).write(vals)
        if self.name == 'A':
            raise ValidationError('the first existing child should not be changed when adding a new child to the parent')
        return res


class ModelParentM2o(models.Model):
    _name = 'test_new_api.model_parent_m2o'
    _description = 'dummy model with multiple childs'

    name = fields.Char('Name')
    child_ids = fields.One2many('test_new_api.model_child_m2o', 'parent_id', string="Children")
    cost = fields.Integer(compute='_compute_cost', store=True)

    @api.depends('child_ids.cost')
    def _compute_cost(self):
        for record in self:
            record.cost = sum(child.cost for child in record.child_ids)


class Country(models.Model):
    _name = 'test_new_api.country'
    _description = 'Country, ordered by name'
    _order = 'name, id'

    name = fields.Char()


class City(models.Model):
    _name = 'test_new_api.city'
    _description = 'City, ordered by country then name'
    _order = 'country_id, name, id'

    name = fields.Char()
    country_id = fields.Many2one('test_new_api.country')

# abstract model with a selection field
class StateMixin(models.AbstractModel):
    _name = 'test_new_api.state_mixin'
    _description = 'Dummy state mixin model'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ])


class SelectionBase(models.Model):
    _name = 'test_new_api.model_selection_base'
    _description = "Model with a base selection field"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ])


class SelectionBaseNullExplicit(models.Model):
    _inherit = 'test_new_api.model_selection_base'
    _description = "Model with a selection field extension with ondelete null"

    my_selection = fields.Selection(selection_add=[
        ('quux', "Quux"),
    ], ondelete={'quux': 'set null'})


class SelectionBaseNullImplicit(models.Model):
    _inherit = 'test_new_api.model_selection_base'
    _description = "Model with a selection field extension without ondelete"

    my_selection = fields.Selection(selection_add=[
        ('ham', "Ham"),
    ])


class SelectionRelated(models.Model):
    _name = 'test_new_api.model_selection_related'
    _description = "Model with a related selection field"

    selection_id = fields.Many2one(
        comodel_name='test_new_api.model_selection_base',
        required=True,
    )
    related_selection = fields.Selection(
        related='selection_id.my_selection',
    )


class SelectionRelatedUpdatable(models.Model):
    _name = 'test_new_api.model_selection_related_updatable'
    _description = "Model with an updatable related selection field"

    selection_id = fields.Many2one(
        comodel_name='test_new_api.model_selection_base',
        required=True,
    )
    related_selection = fields.Selection(
        related='selection_id.my_selection',
        readonly=False,
    )


class SelectionRequired(models.Model):
    _name = 'test_new_api.model_selection_required'
    _description = "Model with a required selection field"

    active = fields.Boolean(default=True)
    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], required=True, default='foo')


class SelectionRequiredDefault(models.Model):
    _inherit = 'test_new_api.model_selection_required'
    _description = "Model with a selection field extension with ondelete default"

    my_selection = fields.Selection(selection_add=[
        ('baz', "Baz"),
    ], ondelete={'baz': 'set default'})


class SelectionRequiredCascade(models.Model):
    _inherit = 'test_new_api.model_selection_required'
    _description = "Model with a selection field extension with ondelete cascade"

    my_selection = fields.Selection(selection_add=[
        ('eggs', "Eggs"),
    ], ondelete={'eggs': 'cascade'})


class SelectionRequiredLiteral(models.Model):
    _inherit = 'test_new_api.model_selection_required'
    _description = "Model with a selection field extension with ondelete set <option>"

    my_selection = fields.Selection(selection_add=[
        ('bacon', "Bacon"),
    ], ondelete={'bacon': 'set bar'})


class SelectionRequiredMultiple(models.Model):
    _inherit = 'test_new_api.model_selection_required'
    _description = "Model with a selection field extension with multiple ondelete policies"

    my_selection = fields.Selection(selection_add=[
        ('pikachu', "Pikachu"),
        ('eevee', "Eevee"),
    ], ondelete={'pikachu': 'set default', 'eevee': lambda r: r.write({'my_selection': 'bar'})})


class SelectionRequiredCallback(models.Model):
    _inherit = 'test_new_api.model_selection_required'
    _description = "Model with a selection field extension with ondelete callback"

    my_selection = fields.Selection(selection_add=[
        ('knickers', "Oh la la"),
    ], ondelete={
        'knickers': lambda recs: recs.write({'active': False, 'my_selection': 'foo'}),
    })


class SelectionNonStored(models.Model):
    _name = 'test_new_api.model_selection_non_stored'
    _description = "Model with non-stored selection field"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], store=False)


class SelectionRequiredForWriteOverride(models.Model):
    _name = 'test_new_api.model_selection_required_for_write_override'
    _description = "Model with required selection field for an extension with write override"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], required=True, default='foo')


class SelectionRequiredWithWriteOverride(models.Model):
    _inherit = 'test_new_api.model_selection_required_for_write_override'

    my_selection = fields.Selection(selection_add=[
        ('divinity', "Divinity: Original Sin 2"),
    ], ondelete={'divinity': 'set default'})

    def write(self, vals):
        if 'my_selection' in vals:
            raise ValueError("No... no no no")
        return super().write(vals)


# Special classes to ensure the correct usage of a shared cache amongst users.
# See the method test_shared_cache_computed_field
class SharedCacheComputeParent(models.Model):
    _name = 'test_new_api.model_shared_cache_compute_parent'
    _description = 'model_shared_cache_compute_parent'

    name = fields.Char(string="Task Name")
    line_ids = fields.One2many(
        'test_new_api.model_shared_cache_compute_line', 'parent_id', string="Timesheets")
    total_amount = fields.Integer(compute='_compute_total_amount', store=True, compute_sudo=True)

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for parent in self:
            parent.total_amount = sum(parent.line_ids.mapped('amount'))


class ShareCacheComputeLine(models.Model):
    _name = 'test_new_api.model_shared_cache_compute_line'
    _description = 'model_shared_cache_compute_line'

    parent_id = fields.Many2one('test_new_api.model_shared_cache_compute_parent')
    amount = fields.Integer()
    user_id = fields.Many2one('res.users', default= lambda self: self.env.user)  # Note: There is an ir.rule about this.


class ComputeContainer(models.Model):
    _name = _description = 'test_new_api.compute.container'

    name = fields.Char()
    member_ids = fields.One2many('test_new_api.compute.member', 'container_id')
    member_count = fields.Integer(compute='_compute_member_count', store=True)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)


class ComputeMember(models.Model):
    _name = _description = 'test_new_api.compute.member'

    name = fields.Char()
    container_id = fields.Many2one('test_new_api.compute.container', compute='_compute_container', store=True)

    @api.depends('name')
    def _compute_container(self):
        container = self.env['test_new_api.compute.container']
        for member in self:
            member.container_id = container.search([('name', '=', member.name)], limit=1)


class User(models.Model):
    _name = _description = 'test_new_api.user'

    group_ids = fields.Many2many('test_new_api.group')
    group_count = fields.Integer(compute='_compute_group_count', store=True)

    @api.depends('group_ids')
    def _compute_group_count(self):
        for user in self:
            user.group_count = len(user.group_ids)


class Group(models.Model):
    _name = _description = 'test_new_api.group'

    user_ids = fields.Many2many('test_new_api.user')


class ComputeEditable(models.Model):
    _name = _description = 'test_new_api.compute_editable'

    line_ids = fields.One2many('test_new_api.compute_editable.line', 'parent_id')

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for line in self.line_ids:
            # even if 'same' is not in the view, it should be the same as 'value'
            line.count += line.same


class ComputeEditableLine(models.Model):
    _name = _description = 'test_new_api.compute_editable.line'

    parent_id = fields.Many2one('test_new_api.compute_editable')
    value = fields.Integer()
    same = fields.Integer(compute='_compute_same', store=True)
    edit = fields.Integer(compute='_compute_edit', store=True, readonly=False)
    count = fields.Integer()

    @api.depends('value')
    def _compute_same(self):
        for line in self:
            line.same = line.value

    @api.depends('value')
    def _compute_edit(self):
        for line in self:
            line.edit = line.value


class ConstrainedUnlinks(models.Model):
    _name = 'test_new_api.model_constrained_unlinks'
    _description = 'Model with unlink override that is constrained'

    foo = fields.Char()
    bar = fields.Integer()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_bar_gt_five(self):
        for rec in self:
            if rec.bar and rec.bar > 5:
                raise ValueError("Nooooooooo bar can't be greater than five!!")

    @api.ondelete(at_uninstall=True)
    def _unlink_except_prosciutto(self):
        for rec in self:
            if rec.foo and rec.foo == 'prosciutto':
                raise ValueError("You didn't say if you wanted it crudo or cotto...")


class TriggerLeft(models.Model):
    _name = 'test_new_api.trigger.left'
    _description = 'model with a related many2one'

    middle_ids = fields.One2many('test_new_api.trigger.middle', 'left_id')
    right_id = fields.Many2one(related='middle_ids.right_id', store=True)


class TriggerMiddle(models.Model):
    _name = 'test_new_api.trigger.middle'
    _description = 'model linking test_new_api.trigger.left and test_new_api.trigger.right'

    left_id = fields.Many2one('test_new_api.trigger.left', required=True)
    right_id = fields.Many2one('test_new_api.trigger.right', required=True)


class TriggerRight(models.Model):
    _name = 'test_new_api.trigger.right'
    _description = 'model with a dependency on the inverse of the related many2one'

    left_ids = fields.One2many('test_new_api.trigger.left', 'right_id')
    left_size = fields.Integer(compute='_compute_left_size', store=True)

    @api.depends('left_ids')
    def _compute_left_size(self):
        for record in self:
            record.left_size = len(record.left_ids)


class Crew(models.Model):
    _name = 'test_new_api.crew'
    _description = 'All yaaaaaarrrrr by ship'
    _table = 'test_new_api_crew'

    # this actually represents the union of two relations pirate/ship and
    # prisoner/ship, where some of the many2one fields can be NULL
    pirate_id = fields.Many2one('test_new_api.pirate')
    prisoner_id = fields.Many2one('test_new_api.prisoner')
    ship_id = fields.Many2one('test_new_api.ship')


class Ship(models.Model):
    _name = 'test_new_api.ship'
    _description = 'Yaaaarrr machine'

    name = fields.Char('Name')
    pirate_ids = fields.Many2many('test_new_api.pirate', 'test_new_api_crew', 'ship_id', 'pirate_id')
    prisoner_ids = fields.Many2many('test_new_api.prisoner', 'test_new_api_crew', 'ship_id', 'prisoner_id')


class Pirate(models.Model):
    _name = 'test_new_api.pirate'
    _description = 'Yaaarrr'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_new_api.ship', 'test_new_api_crew', 'pirate_id', 'ship_id')


class Prisoner(models.Model):
    _name = 'test_new_api.prisoner'
    _description = 'Yaaarrr minions'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_new_api.ship', 'test_new_api_crew', 'prisoner_id', 'ship_id')


class Precompute(models.Model):
    _name = 'test_new_api.precompute'
    _description = 'model with precomputed fields'

    name = fields.Char(required=True)

    # both fields are precomputed
    lower = fields.Char(compute='_compute_names', store=True, precompute=True)
    upper = fields.Char(compute='_compute_names', store=True, precompute=True)

    # precomputed that depends on precomputed fields
    lowup = fields.Char(compute='_compute_lowup', store=True, precompute=True)

    # kind of precomputed related field traversing a many2one
    partner_id = fields.Many2one('res.partner')
    commercial_id = fields.Many2one('res.partner', compute='_compute_commercial_id',
                                    store=True, precompute=True)

    # precomputed depending on one2many fields
    line_ids = fields.One2many('test_new_api.precompute.line', 'parent_id')
    size = fields.Integer(compute='_compute_size', store=True, precompute=True)

    @api.depends('name')
    def _compute_names(self):
        for record in self:
            record.lower = (record.name or "").lower()
            record.upper = (record.name or "").upper()

    @api.depends('lower', 'upper')
    def _compute_lowup(self):
        for record in self:
            record.lowup = record.lower + record.upper

    @api.depends('partner_id.commercial_partner_id')
    def _compute_commercial_id(self):
        for record in self:
            record.commercial_id = record.partner_id.commercial_partner_id

    @api.depends('line_ids.size')
    def _compute_size(self):
        for record in self:
            record.size = sum(record.line_ids.mapped('size'))


class PrecomputeLine(models.Model):
    _name = 'test_new_api.precompute.line'
    _description = 'secondary model with precomputed fields'

    parent_id = fields.Many2one('test_new_api.precompute')
    name = fields.Char(required=True)
    size = fields.Integer(compute='_compute_size', store=True, precompute=True)

    @api.depends('name')
    def _compute_size(self):
        for line in self:
            line.size = len(line.name or "")


class PrecomputeCombo(models.Model):
    _name = 'test_new_api.precompute.combo'
    _description = 'yet another model with precomputed fields'

    name = fields.Char()
    reader = fields.Char(compute='_compute_reader', precompute=True, store=True)
    editer = fields.Char(compute='_compute_editer', precompute=True, store=True, readonly=False)
    setter = fields.Char(compute='_compute_setter', precompute=True, inverse='_inverse_setter', store=True)

    @api.depends('name')
    def _compute_reader(self):
        for record in self:
            record.reader = record.name

    @api.depends('name')
    def _compute_editer(self):
        for record in self:
            record.editer = record.name

    @api.depends('name')
    def _compute_setter(self):
        for record in self:
            record.setter = record.name

    def _inverse_setter(self):
        _logger.warning("Unexpected inverse of %s.setter", self._name, stack_info=True)


class PrecomputeEditable(models.Model):
    _name = 'test_new_api.precompute.editable'
    _description = 'yet another model with precomputed editable fields'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', precompute=True, store=True, readonly=False)
    baz = fields.Char(compute='_compute_baz', precompute=True, store=True, readonly=False)
    baz2 = fields.Char(compute='_compute_baz2', precompute=True, store=True)

    @api.depends('foo')
    def _compute_bar(self):
        self.bar = "COMPUTED"

    @api.depends('bar')
    def _compute_baz(self):
        self.baz = "COMPUTED"

    @api.depends('baz')
    def _compute_baz2(self):
        # this field is a trick to get the value of baz if it ever is recomputed
        # during the precomputation of bar
        for record in self:
            record.baz2 = record.baz


class PrecomputeReadonly(models.Model):
    _name = 'test_new_api.precompute.readonly'
    _description = 'a model with precomputed readonly fields'

    foo = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft')
    bar = fields.Char(compute='_compute_bar', precompute=True, store=True, readonly=True)
    baz = fields.Char(
        compute='_compute_baz', precompute=True, store=True, readonly=True, states={'draft': [('readonly', False)]}
    )

    @api.depends('foo')
    def _compute_bar(self):
        self.bar = "COMPUTED"

    @api.depends('bar')
    def _compute_baz(self):
        self.baz = "COMPUTED"


class PrecomputeRequired(models.Model):
    _name = 'test_new_api.precompute.required'
    _description = 'a model with precomputed required fields'

    partner_id = fields.Many2one('res.partner', required=True)
    name = fields.Char(related='partner_id.name', precompute=True, store=True, required=True)


class PrecomputeMonetary(models.Model):
    _name = 'test_new_api.precompute.monetary'
    _description = 'a model with precomputed monetary and currency'

    amount = fields.Monetary(
        compute='_compute_amount', store=True, precompute=True)
    currency_id = fields.Many2one(
        'res.currency', compute="_compute_currency_id", store=True, precompute=True)

    def _compute_amount(self):
        for record in self:
            record.amount = 12.333

    def _compute_currency_id(self):
        self.currency_id = 1  # EUR


class Prefetch(models.Model):
    _name = 'test_new_api.prefetch'
    _description = 'A model to check the prefetching of fields (translated and group)'

    name = fields.Char('Name', translate=True)
    description = fields.Char('Description', translate=True)
    html_description = fields.Html('Styled description', translate=True)
    rare_description = fields.Char('Rare Description', translate=True, prefetch=False)
    rare_html_description = fields.Html('Rare Styled description', translate=True, prefetch=False)
    harry = fields.Integer('Harry Potter', prefetch='Harry Potter')
    hermione = fields.Char('Hermione Granger', prefetch='Harry Potter')
    ron = fields.Float('Ron Weasley', prefetch='Harry Potter')
    hansel = fields.Integer('Hansel', prefetch="Hansel and Gretel")
    gretel = fields.Char('Gretel', prefetch="Hansel and Gretel")


class Modified(models.Model):
    _name = 'test_new_api.modified'
    _description = 'A model to check modified trigger'

    name = fields.Char('Name')
    line_ids = fields.One2many('test_new_api.modified.line', 'modified_id')
    total_quantity = fields.Integer(compute='_compute_total_quantity')

    @api.depends('line_ids.quantity')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))


class ModifiedLine(models.Model):
    _name = 'test_new_api.modified.line'
    _description = 'A model to check modified trigger'

    modified_id = fields.Many2one('test_new_api.modified')
    modified_name = fields.Char(related="modified_id.name")
    quantity = fields.Integer()
    price = fields.Float()
    total_price = fields.Float(compute='_compute_total_quantity', recursive=True)
    total_price_quantity = fields.Float(compute='_compute_total_price_quantity')

    parent_id = fields.Many2one('test_new_api.modified.line')
    child_ids = fields.One2many('test_new_api.modified.line', 'parent_id')

    @api.depends('price', 'child_ids.total_price', 'child_ids.price')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_price = sum(rec.child_ids.mapped('total_price')) + rec.price

    @api.depends('total_price', 'quantity')
    def _compute_total_price_quantity(self):
        for rec in self:
            rec.total_price_quantity = rec.total_price * rec.quantity


class RelatedTranslation(models.Model):
    _name = 'test_new_api.related_translation_1'
    _description = 'A model to test translation for related fields'

    name = fields.Char('Name', translate=True)
    html = fields.Html('HTML', translate=html_translate)


class RelatedTranslation2(models.Model):
    _name = 'test_new_api.related_translation_2'
    _description = 'A model to test translation for related fields'

    parent_id = fields.Many2one('test_new_api.related_translation_1', string='Parent Model')
    name = fields.Char('Name Related', related='parent_id.name', readonly=False)
    html = fields.Html('HTML Related', related='parent_id.html', readonly=False)


class RelatedTranslation3(models.Model):
    _name = 'test_new_api.related_translation_3'
    _description = 'A model to test translation for related fields'

    parent_id = fields.Many2one('test_new_api.related_translation_2', string='Parent Model')
    name = fields.Char('Name Related', related='parent_id.name', readonly=False)
    html = fields.Html('HTML Related', related='parent_id.html', readonly=False)


class IndexedTranslation(models.Model):
    _name = 'test_new_api.indexed_translation'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')

class EmptyChar(models.Model):
    _name = 'test_new_api.empty_char'
    _description = 'A model to test emtpy char'

    name = fields.Char('Name')

class UnlinkContainer(models.Model):
    _name = 'test_new_api.unlink.container'
    _description = 'A container model to test unlink + trigger'

    name = fields.Char('Name', translate=True)

class UnlinkLine(models.Model):
    _name = 'test_new_api.unlink.line'
    _description = 'A line model to test unlink + trigger'

    container_id = fields.Many2one('test_new_api.unlink.container')
    container_name = fields.Char('Container Name', related='container_id.name', store=True)
