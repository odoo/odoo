from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DomainBool(models.Model):
    _name = 'domain.bool'
    _description = 'Boolean Domain'

    bool_true = fields.Boolean('b1', default=True)
    bool_false = fields.Boolean('b2', default=False)
    bool_undefined = fields.Boolean('b3')


class TestOrmEmpty_Int(models.Model):
    _name = 'test_orm.empty_int'
    _description = 'A model to test empty int'

    number = fields.Integer('Number')


class TestOrmEmpty_Char(models.Model):
    _name = 'test_orm.empty_char'
    _description = 'A model to test emtpy char'

    name = fields.Char('Name')


class TestOrmIndexed_Translation(models.Model):
    _name = 'test_orm.indexed_translation'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')


class TestOrmAnyParent(models.Model):
    _name = 'test_orm.any.parent'
    _description = 'Any Parent'

    name = fields.Char()
    child_ids = fields.One2many('test_orm.any.child', 'parent_id')


class TestOrmAnyChild(models.Model):
    _name = 'test_orm.any.child'
    _description = 'Any Child'
    _inherits = {
        'test_orm.any.parent': 'parent_id',
    }

    parent_id = fields.Many2one('test_orm.any.parent', required=True, ondelete='cascade')
    link_sibling_id = fields.Many2one('test_orm.any.child')
    quantity = fields.Integer()
    tag_ids = fields.Many2many('test_orm.any.tag')


class TestOrmAnyTag(models.Model):
    _name = 'test_orm.any.tag'
    _description = 'Any tag'

    name = fields.Char()
    child_ids = fields.Many2many('test_orm.any.child')


class TestOrmMixed(models.Model):
    _name = 'test_orm.mixed'
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


class TestOrmModel_Active_Field(models.Model):
    _name = 'test_orm.model_active_field'
    _description = 'A model with active field'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_orm.model_active_field')
    children_ids = fields.One2many('test_orm.model_active_field', 'parent_id')
    all_children_ids = fields.One2many('test_orm.model_active_field', 'parent_id',
                                       context={'active_test': False})
    active_children_ids = fields.One2many('test_orm.model_active_field', 'parent_id',
                                          context={'active_test': True})
    relatives_ids = fields.Many2many(
        'test_orm.model_active_field',
        'model_active_field_relatives_rel', 'source_id', 'dest_id',
    )
    all_relatives_ids = fields.Many2many(
        'test_orm.model_active_field',
        'model_active_field_relatives_rel', 'source_id', 'dest_id',
        context={'active_test': False},
    )
    parent_active = fields.Boolean(string='Active Parent', related='parent_id.active', store=True)


class TestOrmFoo(models.Model):
    _name = 'test_orm.foo'
    _description = 'Test ORM Foo'

    name = fields.Char()
    value1 = fields.Integer(change_default=True)
    value2 = fields.Integer()
    text = fields.Char(trim=False)


class TestOrmBar(models.Model):
    _name = 'test_orm.bar'
    _description = 'Test ORM Bar'

    name = fields.Char()
    foo = fields.Many2one('test_orm.foo', compute='_compute_foo', search='_search_foo')
    value1 = fields.Integer(related='foo.value1', readonly=False)
    value2 = fields.Integer(related='foo.value2', readonly=False)
    text1 = fields.Char('Text1', related='foo.text', readonly=False)
    text2 = fields.Char('Text2', related='foo.text', readonly=False, trim=True)

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_orm.foo'].search([('name', '=', bar.name)], limit=1)

    def _search_foo(self, operator, value):
        if operator not in ('in', 'any'):
            return NotImplemented
        records = self.env['test_orm.foo'].browse(value)
        return [('name', 'in', records.mapped('name'))]


class TestOrmCategory(models.Model):
    _name = 'test_orm.category'
    _description = 'Test ORM Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_orm.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one('test_orm.category', compute='_compute_root_categ')
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_orm.discussion', 'test_orm_discussion_category',
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


class TestOrmDiscussion(models.Model):
    _name = 'test_orm.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_orm.category',
        'test_orm_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_orm.message', 'discussion', copy=True)
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_orm.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_orm.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_orm.emailmessage', 'discussion')
    important_emails = fields.One2many('test_orm.emailmessage', 'discussion',
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


class TestOrmMessage(models.Model):
    _name = 'test_orm.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_orm.discussion', ondelete='cascade')
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


class TestOrmEmailmessage(models.Model):
    _name = 'test_orm.emailmessage'
    _description = 'Test ORM Email Message'
    _inherits = {'test_orm.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_orm.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')
    active = fields.Boolean('Active Message', related='message.active', store=True, related_sudo=False)
