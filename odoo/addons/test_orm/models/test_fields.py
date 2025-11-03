import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
import itertools

_logger = logging.getLogger('precompute_setter')


class Test_Fields_Category(models.Model):
    _name = 'test_fields.category'
    _description = 'Test ORM Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_fields.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one('test_fields.category', compute='_compute_root_categ')
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_fields.discussion', 'test_fields_discussion_category',
                                   'category', 'discussion')

    _positive_color = models.Constraint(
        'CHECK(color >= 0)',
        "The color code must be positive!",
    )

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
            for parent, child in itertools.pairwise(categories):
                if parent and child:
                    child.parent = parent
            # assign name of last category, and reassign display_name (to normalize it)
            cat.name = names[-1].strip()

    def _fetch_query(self, query, fields):
        # DLE P45: `test_31_prefetch`,
        # with self.assertRaises(AccessError):
        #     cat1.name
        if self.search_count([('id', 'in', self._ids), ('name', '=', 'NOACCESS')]):
            msg = 'Sorry'
            raise AccessError(msg)
        return super()._fetch_query(query, fields)


class Test_Fields_Discussion(models.Model):
    _name = 'test_fields.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_fields.category',
        'test_fields_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_fields.message', 'discussion', copy=True)
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_fields.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_fields.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_fields.emailmessage', 'discussion')
    important_emails = fields.One2many('test_fields.emailmessage', 'discussion',
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


class Test_Fields_Message(models.Model):
    _name = 'test_fields.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_fields.discussion', ondelete='cascade')
    body = fields.Text(index='trigram')
    author = fields.Many2one('res.users', default=lambda self: self.env.user)
    name = fields.Char(string='Title', compute='_compute_name', store=True)
    display_name = fields.Char(string='Abstract')
    size = fields.Integer(compute='_compute_size', search='_search_size')
    double_size = fields.Integer(compute='_compute_double_size')
    discussion_name = fields.Char(related='discussion.name', string="Discussion Name", readonly=False)
    author_partner = fields.Many2one(
        'res.partner', compute='_compute_author_partner',
        search='_search_author_partner')
    important = fields.Boolean()
    label = fields.Char(translate=True)
    priority = fields.Integer()
    active = fields.Boolean(default=True)
    has_important_sibling = fields.Boolean(compute='_compute_has_important_sibling')

    attributes = fields.Properties(
        string='Discussion Properties',
        definition='discussion.attributes_definition',
    )

    @api.depends('discussion.messages.important')
    def _compute_has_important_sibling(self):
        for record in self:
            siblings = record.discussion.with_context(active_test=False).messages - record
            record.has_important_sibling = any(siblings.mapped('important'))

    @api.constrains('author', 'discussion')
    def _check_author(self):
        for message in self.with_context(active_test=False):
            if message.discussion and message.author not in message.discussion.sudo().participants:
                raise ValidationError(self.env._("Author must be among the discussion participants."))

    @api.depends('author.name', 'discussion.name')
    def _compute_name(self):
        for message in self:
            message.name = self.env.context.get('compute_name',
                "[%s] %s" % (message.discussion.name or '', message.author.name or ''))

    @api.constrains('name')
    def _check_name(self):
        # dummy constraint to check on computed field
        for message in self:
            if message.name.startswith("[X]"):
                msg = "No way!"
                raise ValidationError(msg)

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


class Test_Fields_Emailmessage(models.Model):
    _name = 'test_fields.emailmessage'
    _description = 'Test ORM Email Message'
    _inherits = {'test_fields.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_fields.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')
    active = fields.Boolean('Active Message', related='message.active', store=True, related_sudo=False)


class Test_Fields_Multi(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_fields.multi'
    _description = 'Test ORM Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_fields.multi.line', 'multi')
    partners = fields.One2many(related='partner.child_ids')
    tags = fields.Many2many('test_fields.multi.tag', domain=[('name', 'ilike', 'a')])

    @api.onchange('name')
    def _onchange_name(self):
        for line in self.lines:
            line.name = self.name

    @api.onchange('partner')
    def _onchange_partner(self):
        for line in self.lines:
            line.partner = self.partner

    @api.onchange('tags')
    def _onchange_tags(self):
        for line in self.lines:
            line.tags |= self.tags


class Test_Fields_MultiLine(models.Model):
    _name = 'test_fields.multi.line'
    _description = 'Test ORM Multi Line'

    multi = fields.Many2one('test_fields.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one(related='multi.partner', store=True)
    tags = fields.Many2many('test_fields.multi.tag')


class Test_Fields_MultiLine2(models.Model):
    _name = 'test_fields.multi.line2'
    _inherit = ['test_fields.multi.line']
    _description = 'Test ORM Multi Line 2'


class Test_Fields_MultiTag(models.Model):
    _name = 'test_fields.multi.tag'
    _description = 'Test ORM Multi Tag'

    name = fields.Char()

    @api.depends('name')
    @api.depends_context('special_tag')
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if name and self.env.context.get('special_tag'):
                name += "!"
            record.display_name = name or ""


class Test_Fields_Mixed(models.Model):
    _name = 'test_fields.mixed'
    _description = 'Test ORM Mixed'

    foo = fields.Char()
    text = fields.Text()
    truth = fields.Boolean()
    count = fields.Integer()
    number = fields.Float(digits=(10, 2), default=3.14)
    number2 = fields.Float(digits='ORM Precision')
    date = fields.Date()
    moment = fields.Datetime()
    now = fields.Datetime(compute='_compute_now')
    lang = fields.Selection(string='Language', selection='_get_lang')
    reference = fields.Reference(string='Related Document',
        selection='_reference_models')
    comment0 = fields.Html()
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


class Test_Fields_Foo(models.Model):
    _name = 'test_fields.foo'
    _description = 'Test ORM Foo'

    name = fields.Char()
    value1 = fields.Integer(change_default=True)
    value2 = fields.Integer()
    text = fields.Char(trim=False)


class Test_Fields_Bar(models.Model):
    _name = 'test_fields.bar'
    _description = 'Test ORM Bar'

    name = fields.Char()
    foo = fields.Many2one('test_fields.foo', compute='_compute_foo', search='_search_foo')
    value1 = fields.Integer(related='foo.value1', readonly=False)
    value2 = fields.Integer(related='foo.value2', readonly=False)
    text1 = fields.Char('Text1', related='foo.text', readonly=False)
    text2 = fields.Char('Text2', related='foo.text', readonly=False, trim=True)

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_fields.foo'].search([('name', '=', bar.name)], limit=1)

    def _search_foo(self, operator, value):
        if operator not in ('in', 'any'):
            return NotImplemented
        records = self.env['test_fields.foo'].browse(value)
        return [('name', 'in', records.mapped('name'))]


class Test_Fields_Related(models.Model):
    _name = 'test_fields.related'
    _description = 'Test ORM Related'

    name = fields.Char()
    # related fields with a single field
    related_name = fields.Char(related='name', string='A related on Name', readonly=False)
    related_related_name = fields.Char(related='related_name', string='A related on a related on Name', readonly=False)

    message = fields.Many2one('test_fields.message')
    message_name = fields.Text(related="message.body", related_sudo=False, string='Message Body')
    message_currency = fields.Many2one(related="message.author", string='Message Author')

    foo_id = fields.Many2one('test_fields.related_foo')
    foo_ids = fields.Many2many('test_fields.related_foo', string='Foos')

    foo_name = fields.Char('foo_name', related='foo_id.name', related_sudo=False)
    foo_name_sudo = fields.Char('foo_name_sudo', related='foo_id.name', related_sudo=True)

    foo_bar_name = fields.Char('foo_bar_name', related='foo_id.bar_id.name', related_sudo=False)
    foo_bar_name_sudo = fields.Char('foo_bar_name_sudo', related='foo_id.bar_id.name', related_sudo=True)

    foo_id_bar_name = fields.Char('foo_id_bar_name', related='foo_id.bar_name', related_sudo=False)

    foo_bar_id = fields.Many2one(related='foo_id.bar_id', related_sudo=False, string='Bar')
    foo_bar_id_name = fields.Char(related='foo_bar_id.name', related_sudo=False, string='Bar Name')

    foo_bar_sudo_id = fields.Many2one(related='foo_id.bar_id', related_sudo=True, string='Bar Sudo')
    foo_bar_sudo_id_name = fields.Char(related='foo_bar_sudo_id.name', related_sudo=False, string='Bar Sudo Name')

    foo_bar_ids = fields.Many2many(related='foo_id.bar_ids', related_sudo=False)
    foo_bar_sudo_ids = fields.Many2many(related='foo_id.bar_ids', related_sudo=True, string='Bars Sudo')

    foo_foo_ids = fields.One2many(related='foo_id.foo_ids', related_sudo=False, string='Foo Foos')
    foo_foo_sudo_ids = fields.One2many(related='foo_id.foo_ids', related_sudo=True, string='Foo Foos Sudo')

    foo_binary_att = fields.Binary(related='foo_id.binary_att', related_sudo=False)
    foo_binary_att_sudo = fields.Binary(related='foo_id.binary_att', related_sudo=True, string='Binary Att Sudo')

    foo_binary_bin = fields.Binary(related='foo_id.binary_bin', related_sudo=False)
    foo_binary_bin_sudo = fields.Binary(related='foo_id.binary_bin', related_sudo=True, string='Binary Bin Sudo')


class Test_Fields_Related_Foo(models.Model):
    _name = 'test_fields.related_foo'
    _description = 'test_fields.related_foo'

    name = fields.Char()
    bar_id = fields.Many2one('test_fields.related_bar')
    foo_ids = fields.One2many('test_fields.related', 'foo_id', string='Foos')
    bar_ids = fields.Many2many('test_fields.related_bar', string='Bars')
    binary_att = fields.Binary()
    binary_bin = fields.Binary(attachment=False)
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)
    bar_alias = fields.Many2one(related='bar_id', string='bar_alias')

    foo_names = fields.Char(related='foo_ids.name', related_sudo=False, string="Foo Names")
    foo_names_sudo = fields.Char(related='foo_ids.name', related_sudo=True, string="Foo Names Sudo")

    bar_names = fields.Char(related='bar_ids.name', related_sudo=False, string="Bar Names")
    bar_names_sudo = fields.Char(related='bar_ids.name', related_sudo=True, string="Bar Names Sudo")


class Test_Fields_Related_Bar(models.Model):
    _name = 'test_fields.related_bar'
    _description = 'test_fields.related_bar'

    name = fields.Char()
    active = fields.Boolean(default=True)


class Test_Fields_Related_Inherits(models.Model):
    _name = 'test_fields.related_inherits'
    _description = 'test_fields.related_inherits'
    _inherits = {'test_fields.related': 'base_id'}

    base_id = fields.Many2one('test_fields.related', required=True, ondelete='cascade')


class Test_Fields_ComputeReadonly(models.Model):
    _name = 'test_fields.compute.readonly'
    _description = 'Model with a computed readonly field'

    foo = fields.Char(default='')
    bar = fields.Char(compute='_compute_bar', store=True)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = record.foo


class Test_Fields_ComputeInverse(models.Model):
    _name = 'test_fields.compute.inverse'
    _description = 'Model with a computed inversed field'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', inverse='_inverse_bar', store=True)
    baz = fields.Char()
    child_ids = fields.One2many(
        'test_fields.compute.inverse', 'parent_id',
        compute='_compute_child_ids', inverse='_inverse_child_ids', store=True)
    parent_id = fields.Many2one('test_fields.compute.inverse')

    @api.depends('foo')
    def _compute_bar(self):
        self.env.context.get('log', []).append('compute')
        for record in self:
            record.bar = record.foo

    def _inverse_bar(self):
        self.env.context.get('log', []).append('inverse')
        for record in self:
            record.foo = record.bar

    @api.constrains('bar', 'baz')
    def _check_constraint(self):
        if self.env.context.get('log_constraint'):
            self.env.context.get('log', []).append('constraint')

    @api.depends('foo')
    def _compute_child_ids(self):
        for rec in self:
            if rec.foo == 'has one child':
                rec.child_ids = [
                    Command.clear(),
                    Command.create({'foo': 'child'}),
                ]

    def _inverse_child_ids(self):
        for rec in self:
            if any(child.foo == 'child' for child in self.child_ids):
                rec.foo = 'has one child'


class Test_Fields_ComputeSudo(models.Model):
    _name = 'test_fields.compute.sudo'
    _description = 'Model with a compute_sudo field'

    name_for_uid = fields.Char(compute='_compute_name_for_uid', compute_sudo=True)

    @api.depends_context('uid')
    def _compute_name_for_uid(self):
        for record in self:
            record.name_for_uid = self.env.user.name


class Test_Fields_Multi_Compute_Inverse(models.Model):
    """ Model with the same inverse method for several fields. """
    _name = 'test_fields.multi_compute_inverse'
    _description = 'Test ORM Multi Compute Inverse'

    foo = fields.Char(default='', required=True)
    bar1 = fields.Char(compute='_compute_bars', inverse='_inverse_bar1', store=True)
    bar2 = fields.Char(compute='_compute_bars', inverse='_inverse_bar23', store=True)
    bar3 = fields.Char(compute='_compute_bars', inverse='_inverse_bar23', store=True)

    @api.depends('foo')
    def _compute_bars(self):
        self.env.context.get('log', []).append('compute')
        for record in self:
            substrs = record.foo.split('/') + ['', '', '']
            record.bar1, record.bar2, record.bar3 = substrs[:3]

    def _inverse_bar1(self):
        self.env.context.get('log', []).append('inverse1')
        for record in self:
            record.write({'foo': f'{record.bar1}/{record.bar2}/{record.bar3}'})

    def _inverse_bar23(self):
        self.env.context.get('log', []).append('inverse23')
        for record in self:
            record.write({'foo': f'{record.bar1}/{record.bar2}/{record.bar3}'})


class Test_Fields_Move(models.Model):
    _name = 'test_fields.move'
    _description = 'Move'

    line_ids = fields.One2many('test_fields.move_line', 'move_id', domain=[('visible', '=', True)])
    quantity = fields.Integer(compute='_compute_quantity', store=True)
    tag_id = fields.Many2one('test_fields.multi.tag')
    tag_name = fields.Char(related='tag_id.name')
    tag_repeat = fields.Integer()
    tag_string = fields.Char(compute='_compute_tag_string')

    # This field can fool the ORM during onchanges!  When editing a payment
    # record, modified fields are assigned to the parent record.  When
    # determining the dependent records, the ORM looks for the payments related
    # to this record by the field `move_id`.  As this field is an inverse of
    # `move_id`, it uses it.  If that field was not initialized properly, the
    # ORM determines its value to be... empty (instead of the payment record.)
    payment_ids = fields.One2many('test_fields.payment', 'move_id')
    payment_amount = fields.Integer(compute='_compute_payment_amount')

    @api.depends('line_ids.quantity')
    def _compute_quantity(self):
        for record in self:
            record.quantity = sum(line.quantity for line in record.line_ids)

    @api.depends('tag_name', 'tag_repeat')
    def _compute_tag_string(self):
        for record in self:
            record.tag_string = (record.tag_name or "") * record.tag_repeat

    @api.depends('payment_ids.amount')
    def _compute_payment_amount(self):
        for record in self:
            record.payment_amount = sum(payment.amount for payment in record.payment_ids)


class Test_Fields_Move_Line(models.Model):
    _name = 'test_fields.move_line'
    _description = 'Move Line'

    move_id = fields.Many2one('test_fields.move', required=True, ondelete='cascade')
    visible = fields.Boolean(default=True)
    quantity = fields.Integer()


class Test_Fields_Payment(models.Model):
    _name = 'test_fields.payment'
    _description = 'Payment inherits from Move'
    _inherits = {'test_fields.move': 'move_id'}

    move_id = fields.Many2one('test_fields.move', required=True, ondelete='cascade')
    amount = fields.Integer()


class Test_Fields_Order(models.Model):
    _name = 'test_fields.order'
    _description = 'test_fields.order'

    line_ids = fields.One2many('test_fields.order.line', 'order_id')
    line_short_field_name = fields.Integer(index=True)


class Test_Fields_OrderLine(models.Model):
    _name = 'test_fields.order.line'
    _description = 'test_fields.order.line'

    order_id = fields.Many2one('test_fields.order', required=True, ondelete='cascade')
    product = fields.Char()
    reward = fields.Boolean()
    short_field_name = fields.Integer(index=True)
    very_very_very_very_very_long_field_name_1 = fields.Integer(index=True)
    very_very_very_very_very_long_field_name_2 = fields.Integer(index=True)
    has_been_rewarded = fields.Char(compute='_compute_has_been_rewarded', store=True)

    @api.depends('reward')
    def _compute_has_been_rewarded(self):
        for rec in self:
            if rec.reward:
                rec.has_been_rewarded = 'Yes'

    def unlink(self):
        # also delete associated reward lines
        reward_lines = [
            other_line
            for line in self
            if not line.reward
            for other_line in line.order_id.line_ids
            if other_line.reward and other_line.product == line.product
        ]
        self = self.union(*reward_lines)  # noqa: PLW0642
        return super().unlink()


class Test_Fields_Company(models.Model):
    _name = 'test_fields.company'
    _description = 'Test ORM Company'

    foo = fields.Char(company_dependent=True)
    text = fields.Text(company_dependent=True)
    date = fields.Date(company_dependent=True)
    moment = fields.Datetime(company_dependent=True)
    tag_id = fields.Many2one('test_fields.multi.tag', company_dependent=True)
    truth = fields.Boolean(company_dependent=True)
    count = fields.Integer(company_dependent=True)
    phi = fields.Float(company_dependent=True, digits=(2, 5))
    html1 = fields.Html(company_dependent=True, sanitize=False)
    html2 = fields.Html(company_dependent=True, sanitize_attributes=True, strip_classes=True, strip_style=True)
    company_id = fields.Many2one('res.company', company_dependent=True)  # child_of and parent_of is optimized
    partner_id = fields.Many2one('res.partner', company_dependent=True)


class Test_Fields_CompanyAttr(models.Model):
    _name = 'test_fields.company.attr'
    _description = 'Test ORM Company Attribute'

    company = fields.Many2one('test_fields.company')
    quantity = fields.Integer()
    bar = fields.Char(compute='_compute_bar', store=True)

    @api.depends('quantity', 'company.foo')
    def _compute_bar(self):
        for record in self:
            record.bar = (record.company.foo or '') * record.quantity


class Test_Fields_Recursive(models.Model):
    _name = 'test_fields.recursive'
    _description = 'Test ORM Recursive'

    name = fields.Char(required=True)
    parent = fields.Many2one('test_fields.recursive', ondelete='cascade')
    full_name = fields.Char(compute='_compute_full_name', recursive=True)
    display_name = fields.Char(recursive=True, store=True)
    context_dependent_name = fields.Char(compute='_compute_context_dependent_name', recursive=True)

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

    # This field is recursive, non-stored and context-dependent. Its purpose is
    # to reproduce a bug in modified(), which might not detect that the field
    # is present in cache if it has values in another context.
    @api.depends_context('bozo')
    @api.depends('name', 'parent.context_dependent_name')
    def _compute_context_dependent_name(self):
        for rec in self:
            if rec.parent:
                rec.context_dependent_name = rec.parent.context_dependent_name + " / " + rec.name
            else:
                rec.context_dependent_name = rec.name


class Test_Fields_RecursiveTree(models.Model):
    _name = 'test_fields.recursive.tree'
    _description = 'Test ORM Recursive with one2many field'

    name = fields.Char(required=True)
    parent_id = fields.Many2one('test_fields.recursive.tree', ondelete='cascade')
    children_ids = fields.One2many('test_fields.recursive.tree', 'parent_id')
    display_name = fields.Char(recursive=True, store=True)

    @api.depends('name', 'children_ids.display_name')
    def _compute_display_name(self):
        for rec in self:
            children_names = rec.mapped('children_ids.display_name')
            rec.display_name = '%s(%s)' % (rec.name, ', '.join(children_names))


class Test_Fields_RecursiveOrder(models.Model):
    _name = 'test_fields.recursive.order'
    _description = 'test_fields.recursive.order'

    value = fields.Integer()


class Test_Fields_RecursiveLine(models.Model):
    _name = 'test_fields.recursive.line'
    _description = 'test_fields.recursive.line'

    order_id = fields.Many2one('test_fields.recursive.order')
    task_ids = fields.One2many('test_fields.recursive.task', 'line_id')
    task_number = fields.Integer(compute='_compute_task_number', store=True)

    # line.task_number indirectly depends on recursive field task.line_id, and
    # is triggered by the recursion in modified() on field task.line_id
    @api.depends('task_ids')
    def _compute_task_number(self):
        for record in self:
            record.task_number = len(record.task_ids)


class Test_Fields_RecursiveTask(models.Model):
    _name = 'test_fields.recursive.task'
    _description = 'test_fields.recursive.task'

    value = fields.Integer()
    line_id = fields.Many2one('test_fields.recursive.line',
                              compute='_compute_line_id', recursive=True, store=True)

    # the recursive nature of task.line_id is a bit artificial, but it makes
    # line.task_number be triggered by a recursive call in modified()
    @api.depends('value', 'line_id.order_id.value')
    def _compute_line_id(self):
        # this assignment forces the new value of record.line_id to be dirty in cache
        self.line_id = False
        for record in self:
            domain = [('order_id.value', '=', record.value)]
            record.line_id = record.line_id.search(domain, order='id desc', limit=1)


class Test_Fields_Cascade(models.Model):
    _name = 'test_fields.cascade'
    _description = 'Test ORM Cascade'

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


class Test_Fields_ComputeReadwrite(models.Model):
    _name = 'test_fields.compute.readwrite'
    _description = 'Model with a computed non-readonly field'

    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', store=True, readonly=False)

    @api.depends('foo')
    def _compute_bar(self):
        for record in self:
            record.bar = record.foo


class Test_Fields_ComputeOnchange(models.Model):
    _name = 'test_fields.compute.onchange'
    _description = "Compute method as an onchange"

    active = fields.Boolean()
    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar', store=True)
    baz = fields.Char(compute='_compute_baz', store=True, readonly=False)
    quux = fields.Char(compute='_compute_quux')
    count = fields.Integer(default=0)
    line_ids = fields.One2many(
        'test_fields.compute.onchange.line', 'record_id',
        compute='_compute_line_ids', store=True, readonly=False,
    )
    tag_ids = fields.Many2many(
        'test_fields.multi.tag',
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

    # special case: this field has no dependency
    def _compute_quux(self):
        self.quux = "quux"

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
        Tag = self.env['test_fields.multi.tag']
        for record in self:
            if record.foo:
                record.tag_ids = Tag.search([('name', '=', record.foo)])

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, foo=self.env._("%s (copy)", record.foo)) for record, vals in zip(self, vals_list)]


class Test_Fields_ComputeOnchangeLine(models.Model):
    _name = 'test_fields.compute.onchange.line'
    _description = "Line-like model for test_fields.compute.onchange"

    record_id = fields.Many2one('test_fields.compute.onchange', ondelete='cascade')
    foo = fields.Char()
    bar = fields.Char(compute='_compute_bar')

    @api.depends('foo')
    def _compute_bar(self):
        for line in self:
            line.bar = (line.foo or "") + "r"


class Test_Fields_ComputeDynamicDepends(models.Model):
    _name = 'test_fields.compute.dynamic.depends'
    _description = "Computed field with dynamic dependencies"

    name1 = fields.Char()
    name2 = fields.Char()
    name3 = fields.Char()
    full_name = fields.Char(compute='_compute_full_name')

    def _get_full_name_fields(self):
        # the fields to use are stored in a config parameter
        depends = self.env['ir.config_parameter'].get_str('test_fields.full_name')
        return depends.split(',') if depends else []

    @api.depends(lambda self: self._get_full_name_fields())
    def _compute_full_name(self):
        fnames = self._get_full_name_fields()
        for record in self:
            record.full_name = ", ".join(filter(None, (record[fname] for fname in fnames)))


class Test_Fields_ComputeUnassigned(models.Model):
    _name = 'test_fields.compute.unassigned'
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


class Test_Fields_Model_Binary(models.Model):
    _name = 'test_fields.model_binary'
    _description = 'Test Image field'

    binary = fields.Binary()
    binary_x_filename = fields.Char()
    binary_x_filename2 = fields.Char()
    binary_related_store = fields.Binary("Binary Related Store", related='binary', store=True, readonly=False)
    binary_related_no_store = fields.Binary("Binary Related No Store", related='binary', store=False, readonly=False)
    binary_computed = fields.Binary(compute='_compute_binary')

    @api.depends('binary')
    def _compute_binary(self):
        # arbitrary value: 'bin_size' must have no effect
        for record in self:
            record.binary_computed = [(record.id, bool(record.binary))]


class Test_Fields_Model_Image(models.Model):
    _name = 'test_fields.model_image'
    _description = 'Test Image field'

    name = fields.Char(required=True)

    image = fields.Image()
    image_512 = fields.Image("Image 512", related='image', max_width=512, max_height=512, store=True, readonly=False)
    image_256 = fields.Image("Image 256", related='image', max_width=256, max_height=256, store=False, readonly=False)
    image_128 = fields.Image("Image 128", max_width=128, max_height=128)
    image_64 = fields.Image("Image 64", related='image', max_width=64, max_height=64, store=True, attachment=False, readonly=False)


class Test_Fields_Binary_Svg(models.Model):
    _name = 'test_fields.binary_svg'
    _description = 'Test SVG upload'

    name = fields.Char(required=True)
    image_attachment = fields.Binary(attachment=True)
    image_wo_attachment = fields.Binary(attachment=False)
    image_wo_attachment_related = fields.Binary(
        "image wo attachment", related="image_wo_attachment",
        store=True, attachment=False,
    )


class Test_Fields_Monetary_Base(models.Model):
    _name = 'test_fields.monetary_base'
    _description = 'Monetary Base'

    base_currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary(currency_field='base_currency_id')


class Test_Fields_Monetary_Related(models.Model):
    _name = 'test_fields.monetary_related'
    _description = 'Monetary Related'

    monetary_id = fields.Many2one('test_fields.monetary_base')
    currency_id = fields.Many2one('res.currency', related='monetary_id.base_currency_id')
    amount = fields.Monetary(related='monetary_id.amount')
    total = fields.Monetary()


class Test_Fields_Monetary_Custom(models.Model):
    _name = 'test_fields.monetary_custom'
    _description = 'Monetary Related Custom'

    monetary_id = fields.Many2one('test_fields.monetary_base')
    x_currency_id = fields.Many2one('res.currency', related='monetary_id.base_currency_id')
    x_amount = fields.Monetary(related='monetary_id.amount')


class Test_Fields_Monetary_Inherits(models.Model):
    _name = 'test_fields.monetary_inherits'
    _description = 'Monetary Inherits'
    _inherits = {'test_fields.monetary_base': 'monetary_id'}

    monetary_id = fields.Many2one('test_fields.monetary_base', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency')


class Test_Fields_Monetary_Order(models.Model):
    _name = 'test_fields.monetary_order'
    _description = 'Sales Order'

    currency_id = fields.Many2one('res.currency')
    line_ids = fields.One2many('test_fields.monetary_order_line', 'order_id')
    total = fields.Monetary(compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for record in self:
            record.total = sum(line.subtotal for line in record.line_ids)


class Test_Fields_Monetary_Order_Line(models.Model):
    _name = 'test_fields.monetary_order_line'
    _description = 'Sales Order Line'

    order_id = fields.Many2one('test_fields.monetary_order', required=True, ondelete='cascade')
    subtotal = fields.Float(digits=(10, 2))


class Test_Fields_Selection(models.Model):
    _name = 'test_fields.selection'
    _description = "Selection"

    state = fields.Selection([('foo', 'Foo'), ('bar', 'Bar')])
    other = fields.Selection([('foo', 'Foo'), ('bar', 'Bar')])


class Test_Fields_Req_M2o(models.Model):
    _name = 'test_fields.req_m2o'
    _description = 'Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='cascade')
    bar = fields.Many2one('res.country', required=True)


class Test_Fields_Req_M2o_Transient(models.TransientModel):
    _name = 'test_fields.req_m2o_transient'
    _description = 'Transient Model with Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='restrict')
    bar = fields.Many2one('res.country', required=True)


class Test_Fields_Model_A(models.Model):
    _name = 'test_fields.model_a'
    _description = 'Model A'

    name = fields.Char()
    a_restricted_b_ids = fields.Many2many('test_fields.model_b', relation='rel_model_fields_a_model_b_1')
    b_restricted_b_ids = fields.Many2many('test_fields.model_b', relation='rel_model_fields_a_model_b_2', ondelete='restrict')


class Test_Fields_Model_B(models.Model):
    _name = 'test_fields.model_b'
    _description = 'Model B'

    name = fields.Char()
    a_restricted_a_ids = fields.Many2many('test_fields.model_a', relation='rel_model_fields_a_model_b_1', ondelete='restrict')
    b_restricted_a_ids = fields.Many2many('test_fields.model_a', relation='rel_model_fields_a_model_b_2')


# model with explicit and stored field 'display_name'
class Test_Fields_Display(models.Model):
    _name = 'test_fields.display'
    _description = 'Model that overrides display_name'

    display_name = fields.Char(store=True)

    def _compute_display_name(self):
        for record in self:
            record.display_name = 'My id is %s' % (record.id)


# abstract model with automatic and non-stored field 'display_name'
class Test_Fields_Mixin(models.AbstractModel):
    _name = 'test_fields.mixin'
    _description = 'Dummy mixin model'


# in this model extension, the field 'display_name' should not be inherited from


# pylint: disable=E0102
class Test_Fields_Display(models.Model):  # noqa: F811
    _name = 'test_fields.display'
    _inherit = ['test_fields.mixin', 'test_fields.display']


class Test_Fields_Model_Active_Field(models.Model):
    _name = 'test_fields.model_active_field'
    _description = 'A model with active field'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_fields.model_active_field')
    children_ids = fields.One2many('test_fields.model_active_field', 'parent_id')
    all_children_ids = fields.One2many('test_fields.model_active_field', 'parent_id',
                                       context={'active_test': False})
    active_children_ids = fields.One2many('test_fields.model_active_field', 'parent_id',
                                          context={'active_test': True})
    relatives_ids = fields.Many2many(
        'test_fields.model_active_field',
        'model_fields_active_field_relatives_rel', 'source_id', 'dest_id',
    )
    all_relatives_ids = fields.Many2many(
        'test_fields.model_active_field',
        'model_fields_active_field_relatives_rel', 'source_id', 'dest_id',
        context={'active_test': False},
    )
    parent_active = fields.Boolean(string='Active Parent', related='parent_id.active', store=True)


class Test_Fields_Model_Many2one_Reference(models.Model):
    _name = 'test_fields.model_many2one_reference'
    _description = 'dummy m2oref model'

    res_model = fields.Char('Resource Model')
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model')
    const = fields.Boolean(default=True)


class Test_Fields_Inverse_M2o_Ref(models.Model):
    _name = 'test_fields.inverse_m2o_ref'
    _description = 'dummy m2oref inverse model'

    model_ids = fields.One2many(
        'test_fields.model_many2one_reference', 'res_id',
        string="Models", domain=[('const', '=', True)])
    model_ids_count = fields.Integer("Count", compute='_compute_model_ids_count')
    model_computed_ids = fields.One2many(
        'test_fields.model_many2one_reference',
        string="Models Computed",
        compute='_compute_model_computed_ids',
    )

    @api.depends('model_ids')
    def _compute_model_ids_count(self):
        for rec in self:
            rec.model_ids_count = len(rec.model_ids)

    def _compute_model_computed_ids(self):
        self.model_computed_ids = []


class Test_Fields_Country(models.Model):
    _name = 'test_fields.country'
    _description = 'Country, ordered by name'
    _order = 'name, id'

    name = fields.Char()


class Test_Fields_City(models.Model):
    _name = 'test_fields.city'
    _description = 'City, ordered by country then name'
    _order = 'country_id, name, id'

    name = fields.Char()
    country_id = fields.Many2one('test_fields.country')


# abstract model with a selection field
class Test_Fields_State_Mixin(models.AbstractModel):
    _name = 'test_fields.state_mixin'
    _description = 'Dummy state mixin model'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ])


class Test_Fields_Model_Selection_Base(models.Model):
    _name = 'test_fields.model_selection_base'
    _description = "Model with a base selection field"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ])


# pylint: disable=E0102
class Test_Fields_Model_Selection_Base(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_base'
    _description = "Model with a selection field extension with ondelete null"

    my_selection = fields.Selection(selection_add=[
        ('quux', "Quux"),
    ], ondelete={'quux': 'set null'})


# pylint: disable=E0102
class Test_Fields_Model_Selection_Base(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_base'
    _description = "Model with a selection field extension without ondelete"

    my_selection = fields.Selection(selection_add=[
        ('ham', "Ham"),
    ])


class Test_Fields_Model_Selection_Related(models.Model):
    _name = 'test_fields.model_selection_related'
    _description = "Model with a related selection field"

    selection_id = fields.Many2one(
        comodel_name='test_fields.model_selection_base',
        required=True,
    )
    related_selection = fields.Selection(
        related='selection_id.my_selection',
    )


class Test_Fields_Model_Selection_Related_Updatable(models.Model):
    _name = 'test_fields.model_selection_related_updatable'
    _description = "Model with an updatable related selection field"

    selection_id = fields.Many2one(
        comodel_name='test_fields.model_selection_base',
        required=True,
    )
    related_selection = fields.Selection(
        related='selection_id.my_selection',
        readonly=False,
    )


class Test_Fields_Model_Selection_Required(models.Model):
    _name = 'test_fields.model_selection_required'
    _description = "Model with a required selection field"

    active = fields.Boolean(default=True)
    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], required=True, default='foo')


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required'
    _description = "Model with a selection field extension with ondelete default"

    my_selection = fields.Selection(selection_add=[
        ('baz', "Baz"),
    ], ondelete={'baz': 'set default'})


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required'
    _description = "Model with a selection field extension with ondelete cascade"

    my_selection = fields.Selection(selection_add=[
        ('eggs', "Eggs"),
    ], ondelete={'eggs': 'cascade'})


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required'
    _description = "Model with a selection field extension with ondelete set <option>"

    my_selection = fields.Selection(selection_add=[
        ('bacon', "Bacon"),
    ], ondelete={'bacon': 'set bar'})


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required'
    _description = "Model with a selection field extension with multiple ondelete policies"

    my_selection = fields.Selection(selection_add=[
        ('pikachu', "Pikachu"),
        ('eevee', "Eevee"),
    ], ondelete={'pikachu': 'set default', 'eevee': lambda r: r.write({'my_selection': 'bar'})})


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required'
    _description = "Model with a selection field extension with ondelete callback"

    my_selection = fields.Selection(selection_add=[
        ('knickers', "Oh la la"),
    ], ondelete={
        'knickers': lambda recs: recs.write({'active': False, 'my_selection': 'foo'}),
    })


class Test_Fields_Model_Selection_Non_Stored(models.Model):
    _name = 'test_fields.model_selection_non_stored'
    _description = "Model with non-stored selection field"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], store=False)


class Test_Fields_Model_Selection_Required_For_Write_Override(models.Model):
    _name = 'test_fields.model_selection_required_for_write_override'
    _description = "Model with required selection field for an extension with write override"

    my_selection = fields.Selection([
        ('foo', "Foo"),
        ('bar', "Bar"),
    ], required=True, default='foo')


# pylint: disable=E0102
class Test_Fields_Model_Selection_Required_For_Write_Override(models.Model):  # noqa: F811
    _inherit = 'test_fields.model_selection_required_for_write_override'

    my_selection = fields.Selection(selection_add=[
        ('divinity', "Divinity: Original Sin 2"),
    ], ondelete={'divinity': 'set default'})

    def write(self, vals):
        if 'my_selection' in vals:
            msg = "No... no no no"
            raise ValueError(msg)
        return super().write(vals)


class Test_Fields_ComputeContainer(models.Model):
    _name = 'test_fields.compute.container'
    _description = 'test_fields.compute.container'

    name = fields.Char()
    name_translated = fields.Char(translate=True)
    member_ids = fields.One2many('test_fields.compute.member', 'container_id')
    member_count = fields.Integer(compute='_compute_member_count', store=True)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)


class Test_Fields_ComputeMember(models.Model):
    _name = 'test_fields.compute.member'
    _description = 'test_fields.compute.member'

    name = fields.Char()
    container_id = fields.Many2one('test_fields.compute.container', compute='_compute_container', store=True)
    container_super_id = fields.Many2one(
        'test_fields.compute.container', string='Container For SUPERUSER',
    )
    container_context_id = fields.Many2one(
        'test_fields.compute.container',
        compute='_compute_container_context_id',
        search='_search_container_context',
    )
    container_context_name = fields.Char(
        related='container_context_id.name', string='Container Context Name',
    )
    container_context_name_translated = fields.Char(
        related='container_context_id.name_translated', string='Container Context Name Translated',
    )

    @api.depends('name')
    def _compute_container(self):
        container = self.env['test_fields.compute.container']
        for member in self:
            member.container_id = container.search([('name', '=', member.name)], limit=1)

    @api.depends('container_id', 'container_super_id')
    @api.depends_context('uid')
    def _compute_container_context_id(self):
        field_name = 'container_super_id' if self.env.user._is_superuser() else 'container_id'
        for member in self:
            member.container_context_id = member[field_name]

    def _search_container_context(self, operator, value):
        field_name = 'container_super_id' if self.env.user._is_superuser() else 'container_id'
        return [(field_name, operator, value)]


class Test_Fields_ComputeCreator(models.Model):
    """ This model has a computed field that creates a new record. """
    _name = 'test_fields.compute.creator'
    _description = 'test_fields.compute.creator'

    name = fields.Char()
    created_id = fields.Many2one('test_fields.compute.created', compute='_compute_created', store=True)

    @api.depends('name')
    def _compute_created(self):
        model = self.env['test_fields.compute.created']
        for record in self:
            record.created_id = (
                model.search([('name', '=', record.name)], limit=1)
                or model.create({'name': record.name})
            )


class Test_Fields_ComputeCreated(models.Model):
    """ This model has records created by another model, and has a stored
    computed field. The purpose of that field is to make sure that flushing the
    field above creates a record here and also flushes its computed field.
    """
    _name = 'test_fields.compute.created'
    _description = 'test_fields.compute.created'

    name = fields.Char()
    value = fields.Integer(compute='_compute_value', store=True)

    @api.depends('name')
    def _compute_value(self):
        for record in self:
            record.value = len(record.name or "")


class Test_Fields_User(models.Model):
    _name = 'test_fields.user'
    _description = 'test_fields.user'
    _allow_sudo_commands = False

    name = fields.Char()
    group_ids = fields.Many2many('test_fields.group')
    group_count = fields.Integer(compute='_compute_group_count', store=True)

    @api.depends('group_ids')
    def _compute_group_count(self):
        for user in self:
            user.group_count = len(user.group_ids)


class Test_Fields_Group(models.Model):
    _name = 'test_fields.group'
    _description = 'test_fields.group'
    _allow_sudo_commands = False

    name = fields.Char()
    user_ids = fields.Many2many('test_fields.user')


class Test_Fields_Model_Constrained_Unlinks(models.Model):
    _name = 'test_fields.model_constrained_unlinks'
    _description = 'Model with unlink override that is constrained'

    foo = fields.Char()
    bar = fields.Integer()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_bar_gt_five(self):
        for rec in self:
            if rec.bar and rec.bar > 5:
                msg = "Nooooooooo bar can't be greater than five!!"
                raise ValueError(msg)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_prosciutto(self):
        for rec in self:
            if rec.foo and rec.foo == 'prosciutto':
                msg = "You didn't say if you wanted it crudo or cotto..."
                raise ValueError(msg)


class Test_Fields_TriggerLeft(models.Model):
    _name = 'test_fields.trigger.left'
    _description = 'model with a related many2one'

    middle_ids = fields.One2many('test_fields.trigger.middle', 'left_id')
    right_id = fields.Many2one(related='middle_ids.right_id', store=True)


class Test_Fields_TriggerMiddle(models.Model):
    _name = 'test_fields.trigger.middle'
    _description = 'model linking test_fields.trigger.left and test_fields.trigger.right'

    left_id = fields.Many2one('test_fields.trigger.left', required=True)
    right_id = fields.Many2one('test_fields.trigger.right', required=True)


class Test_Fields_TriggerRight(models.Model):
    _name = 'test_fields.trigger.right'
    _description = 'model with a dependency on the inverse of the related many2one'

    left_ids = fields.One2many('test_fields.trigger.left', 'right_id')
    left_size = fields.Integer(compute='_compute_left_size', store=True)

    @api.depends('left_ids')
    def _compute_left_size(self):
        for record in self:
            record.left_size = len(record.left_ids)


class Test_Fields_Precompute(models.Model):
    _name = 'test_fields.precompute'
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
    line_ids = fields.One2many('test_fields.precompute.line', 'parent_id')
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


class Test_Fields_PrecomputeLine(models.Model):
    _name = 'test_fields.precompute.line'
    _description = 'secondary model with precomputed fields'

    parent_id = fields.Many2one('test_fields.precompute')
    name = fields.Char(required=True)
    size = fields.Integer(compute='_compute_size', store=True, precompute=True)

    @api.depends('name')
    def _compute_size(self):
        for line in self:
            line.size = len(line.name or "")


class Test_Fields_PrecomputeCombo(models.Model):
    _name = 'test_fields.precompute.combo'
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


class Test_Fields_PrecomputeEditable(models.Model):
    _name = 'test_fields.precompute.editable'
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


class Test_Fields_PrecomputeReadonly(models.Model):
    _name = 'test_fields.precompute.readonly'
    _description = 'a model with precomputed readonly fields'

    foo = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft')
    bar = fields.Char(compute='_compute_bar', precompute=True, store=True, readonly=True)
    baz = fields.Char(compute='_compute_baz', precompute=True, store=True, readonly=False)

    @api.depends('foo')
    def _compute_bar(self):
        self.bar = "COMPUTED"

    @api.depends('bar')
    def _compute_baz(self):
        self.baz = "COMPUTED"


class Test_Fields_PrecomputeRequired(models.Model):
    _name = 'test_fields.precompute.required'
    _description = 'a model with precomputed required fields'

    partner_id = fields.Many2one('res.partner', required=True)
    name = fields.Char(related='partner_id.name', precompute=True, store=True, required=True)


class Test_Fields_PrecomputeMonetary(models.Model):
    _name = 'test_fields.precompute.monetary'
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


class Test_Fields_Prefetch(models.Model):
    _name = 'test_fields.prefetch'
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

    line_ids = fields.One2many('test_fields.prefetch.line', 'prefetch_id')


class Test_Fields_PrefetchLine(models.Model):
    _name = 'test_fields.prefetch.line'
    _description = 'test_fields.prefetch.line'

    prefetch_id = fields.Many2one('test_fields.prefetch')
    harry = fields.Integer(related='prefetch_id.harry', store=True)


class Test_Fields_Modified(models.Model):
    _name = 'test_fields.modified'
    _description = 'A model to check modified trigger'

    name = fields.Char('Name')
    line_ids = fields.One2many('test_fields.modified.line', 'modified_id')
    total_quantity = fields.Integer(compute='_compute_total_quantity')

    @api.depends('line_ids.quantity')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))


class Test_Fields_ModifiedLine(models.Model):
    _name = 'test_fields.modified.line'
    _description = 'A model to check modified trigger'

    modified_id = fields.Many2one('test_fields.modified')
    modified_name = fields.Char(related="modified_id.name")
    quantity = fields.Integer()
    price = fields.Float()
    total_price = fields.Float(compute='_compute_total_quantity', recursive=True)
    total_price_quantity = fields.Float(compute='_compute_total_price_quantity')

    parent_id = fields.Many2one('test_fields.modified.line')
    child_ids = fields.One2many('test_fields.modified.line', 'parent_id')

    @api.depends('price', 'child_ids.total_price', 'child_ids.price')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_price = sum(rec.child_ids.mapped('total_price')) + rec.price

    @api.depends('total_price', 'quantity')
    def _compute_total_price_quantity(self):
        for rec in self:
            rec.total_price_quantity = rec.total_price * rec.quantity


class Test_Fields_CreatePerformance(models.Model):
    _name = _description = 'test_fields.create.performance'

    confirmed = fields.Boolean()
    name = fields.Char()
    name_changes = fields.Integer(compute='_compute_name_changes', store=True)
    line_ids = fields.One2many('test_fields.create.performance.line', 'perf_id')
    tag_ids = fields.Many2many('test_fields.create.performance.line', 'test_fields_create_perf_tag_ids')

    @api.depends('name')
    def _compute_name_changes(self):
        for record in self:
            record.name_changes += 1


class Test_Fields_CreatePerformanceLine(models.Model):
    _name = _description = 'test_fields.create.performance.line'

    perf_id = fields.Many2one('test_fields.create.performance')


# See the method test_shared_cache_computed_field
class Test_Fields_Model_Shared_Cache_Compute_Parent(models.Model):
    _name = 'test_fields.model_shared_cache_compute_parent'
    _description = 'model_shared_cache_compute_parent'

    name = fields.Char(string="Task Name")
    line_ids = fields.One2many(
        'test_fields.model_shared_cache_compute_line', 'parent_id', string="Timesheets")
    total_amount = fields.Integer(compute='_compute_total_amount', store=True, compute_sudo=True)

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for parent in self:
            parent.total_amount = sum(parent.line_ids.mapped('amount'))


class Test_Fields_Model_Shared_Cache_Compute_Line(models.Model):
    _name = 'test_fields.model_shared_cache_compute_line'
    _description = 'model_shared_cache_compute_line'

    parent_id = fields.Many2one('test_fields.model_shared_cache_compute_parent')
    amount = fields.Integer()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)  # Note: There is an ir.rule about this.
