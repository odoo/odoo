import itertools

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class TestSearchCategory(models.Model):
    _name = 'test_search.category'
    _description = 'Test ORM Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_search.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one('test_search.category', compute='_compute_root_categ')
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_search.discussion', 'test_search_discussion_category',
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


class TestSearchDiscussion(models.Model):
    _name = 'test_search.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_search.category',
        'test_search_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_search.message', 'discussion', copy=True)
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_search.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_search.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_search.emailmessage', 'discussion')
    important_emails = fields.One2many('test_search.emailmessage', 'discussion',
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


class TestSearchMessage(models.Model):
    _name = 'test_search.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_search.discussion', ondelete='cascade')
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


class TestSearchEmailmessage(models.Model):
    _name = 'test_search.emailmessage'
    _description = 'Test ORM Email Message'
    _inherits = {'test_search.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_search.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')
    active = fields.Boolean('Active Message', related='message.active', store=True, related_sudo=False)


class TestSearchMulti(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_search.multi'
    _description = 'Test ORM Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_search.multi.line', 'multi')
    partners = fields.One2many(related='partner.child_ids')
    tags = fields.Many2many('test_search.multi.tag', domain=[('name', 'ilike', 'a')])

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


class TestSearchMultiLine(models.Model):
    _name = 'test_search.multi.line'
    _description = 'Test ORM Multi Line'

    multi = fields.Many2one('test_search.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one(related='multi.partner', store=True)
    tags = fields.Many2many('test_search.multi.tag')


class TestSearchMultiTag(models.Model):
    _name = 'test_search.multi.tag'
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


class TestSearchHierarchyHead(models.Model):
    _name = 'test_search.hierarchy.head'
    _description = 'Hierarchy Head'

    node_id = fields.Many2one('test_search.hierarchy.node')


class TestSearchHierarchyNode(models.Model):
    _name = 'test_search.hierarchy.node'
    _description = 'Hierarchy Node'

    name = fields.Char()
    parent_id = fields.Many2one('test_search.hierarchy.node')
    child_ids = fields.One2many('test_search.hierarchy.node', inverse_name='parent_id')


class TestSearchRelated(models.Model):
    _name = 'test_search.related'
    _description = 'Test ORM Related'

    name = fields.Char()
    # related fields with a single field
    related_name = fields.Char(related='name', string='A related on Name', readonly=False)
    related_related_name = fields.Char(related='related_name', string='A related on a related on Name', readonly=False)

    message = fields.Many2one('test_search.message')
    message_name = fields.Text(related="message.body", related_sudo=False, string='Message Body')
    message_currency = fields.Many2one(related="message.author", string='Message Author')

    foo_id = fields.Many2one('test_search.related_foo')
    foo_ids = fields.Many2many('test_search.related_foo', string='Foos')

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

    foo_float_id = fields.Float(related='foo_id.test_float')


class TestSearchRelatedFoo(models.Model):
    _name = 'test_search.related_foo'
    _description = 'test_search.related_foo'

    name = fields.Char()
    bar_id = fields.Many2one('test_search.related_bar')
    foo_ids = fields.One2many('test_search.related', 'foo_id', string='Foos')
    bar_ids = fields.Many2many('test_search.related_bar', string='Bars')
    binary_att = fields.Binary()
    binary_bin = fields.Binary(attachment=False)
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)
    bar_alias = fields.Many2one(related='bar_id', string='bar_alias')

    foo_names = fields.Char(related='foo_ids.name', related_sudo=False, string="Foo Names")
    foo_names_sudo = fields.Char(related='foo_ids.name', related_sudo=True, string="Foo Names Sudo")

    bar_names = fields.Char(related='bar_ids.name', related_sudo=False, string="Bar Names")
    bar_names_sudo = fields.Char(related='bar_ids.name', related_sudo=True, string="Bar Names Sudo")

    test_float = fields.Float(digits='ORM Precision')


class TestSearchRelatedBar(models.Model):
    _name = 'test_search.related_bar'
    _description = 'test_search.related_bar'

    name = fields.Char()
    active = fields.Boolean(default=True)


class TestSearchRelatedInherits(models.Model):
    _name = 'test_search.related_inherits'
    _description = 'test_search.related_inherits'
    _inherits = {'test_search.related': 'base_id'}

    base_id = fields.Many2one('test_search.related', required=True, ondelete='cascade')


class TestSearchCountry(models.Model):
    _name = 'test_search.country'
    _description = 'Country, ordered by name'
    _order = 'name, id'

    name = fields.Char()


class TestSearchCity(models.Model):
    _name = 'test_search.city'
    _description = 'City, ordered by country then name'
    _order = 'country_id, name, id'

    name = fields.Char()
    country_id = fields.Many2one('test_search.country')


class TestSearchMove(models.Model):
    _name = 'test_search.move'
    _description = 'Move'

    line_ids = fields.One2many('test_search.move_line', 'move_id', domain=[('visible', '=', True)])
    quantity = fields.Integer(compute='_compute_quantity', store=True)
    tag_id = fields.Many2one('test_search.multi.tag')
    tag_name = fields.Char(related='tag_id.name')
    tag_repeat = fields.Integer()
    tag_string = fields.Char(compute='_compute_tag_string')

    # This field can fool the ORM during onchanges!  When editing a payment
    # record, modified fields are assigned to the parent record.  When
    # determining the dependent records, the ORM looks for the payments related
    # to this record by the field `move_id`.  As this field is an inverse of
    # `move_id`, it uses it.  If that field was not initialized properly, the
    # ORM determines its value to be... empty (instead of the payment record.)
    payment_ids = fields.One2many('test_search.payment', 'move_id')
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


class TestSearchMoveLine(models.Model):
    _name = 'test_search.move_line'
    _description = 'Move Line'

    move_id = fields.Many2one('test_search.move', required=True, ondelete='cascade')
    visible = fields.Boolean(default=True)
    quantity = fields.Integer()


class TestSearchPayment(models.Model):
    _name = 'test_search.payment'
    _description = 'Payment inherits from Move'
    _inherits = {'test_search.move': 'move_id'}

    move_id = fields.Many2one('test_search.move', required=True, ondelete='cascade')
    amount = fields.Integer()


class TestSearchAnyParent(models.Model):
    _name = 'test_search.any.parent'
    _description = 'Any Parent'

    name = fields.Char()
    child_ids = fields.One2many('test_search.any.child', 'parent_id')


class TestSearchAnyChild(models.Model):
    _name = 'test_search.any.child'
    _description = 'Any Child'
    _inherits = {
        'test_search.any.parent': 'parent_id',
    }

    parent_id = fields.Many2one('test_search.any.parent', required=True, ondelete='cascade')
    link_sibling_id = fields.Many2one('test_search.any.child')
    quantity = fields.Integer()
    tag_ids = fields.Many2many('test_search.any.tag')


class TestSearchAnyTag(models.Model):
    _name = 'test_search.any.tag'
    _description = 'Any tag'

    name = fields.Char()
    child_ids = fields.Many2many('test_search.any.child')


class TestSearchCustomView(models.Model):
    _name = 'test_search.custom.view'
    _description = "test_search.custom.view"
    _auto = False
    _depends = {
        'test_search.any.tag': ['name'],
        'test_search.any.child': ['quantity'],
    }

    sum_quantity = fields.Integer()
    tag_id = fields.Many2one('test_search.any.tag')

    def init(self):
        query = """
            CREATE or REPLACE VIEW test_search_custom_view AS (
                SELECT tag.id AS id, SUM(child.quantity) AS sum_quantity, tag.id AS tag_id
                FROM test_search_any_child AS child
                JOIN test_search_any_child_test_search_any_tag_rel AS rel ON rel.test_search_any_child_id = child.id
                JOIN test_search_any_tag AS tag ON tag.id = rel.test_search_any_tag_id
                GROUP BY tag.id
            )
        """
        self.env.cr.execute(query)


class TestSearchCustomTableQuery(models.Model):
    _name = 'test_search.custom.table_query'
    _description = "test_search.custom.table_query"
    _auto = False
    _depends = {
        'test_search.any.tag': ['name'],
        'test_search.any.child': ['quantity'],
    }

    sum_quantity = fields.Integer()
    tag_id = fields.Many2one('test_search.any.tag')

    @property
    def _table_query(self):
        return """
            SELECT tag.id AS id, SUM(child.quantity) AS sum_quantity, tag.id AS tag_id
            FROM test_search_any_child AS child
            JOIN test_search_any_child_test_search_any_tag_rel AS rel ON rel.test_search_any_child_id = child.id
            JOIN test_search_any_tag AS tag ON tag.id = rel.test_search_any_tag_id
            GROUP BY tag.id
        """


class TestSearchCustomTableQuerySql(models.Model):
    _name = 'test_search.custom.table_query_sql'
    _description = "test_search.custom.table_query_sql"
    _auto = False
    _depends = {
        'test_search.any.tag': ['name'],
        'test_search.any.child': ['quantity'],
    }

    sum_quantity = fields.Integer()
    tag_id = fields.Many2one('test_search.any.tag')

    @property
    def _table_query(self):
        return SQL(
            """
            SELECT tag.id AS id, SUM(child.quantity) AS sum_quantity, tag.id AS tag_id
            FROM test_search_any_child AS child
            JOIN test_search_any_child_test_search_any_tag_rel AS rel ON rel.test_search_any_child_id = child.id
            JOIN test_search_any_tag AS tag ON tag.id = rel.test_search_any_tag_id
            GROUP BY tag.id
            """,
        )


class TestSearchCourse(models.Model):
    _name = 'test_search.course'
    _description = 'a course'

    name = fields.Char('Name')
    lesson_ids = fields.One2many('test_search.lesson', 'course_id')
    author_id = fields.Many2one('test_search.person')
    private_field = fields.Char(groups="base.group_no_one")
    reference = fields.Reference(string='reference to lesson', selection='_selection_reference_model')
    m2o_reference_id = fields.Many2oneReference(string='reference to lesson too', model_field='m2o_reference_model')
    m2o_reference_model = fields.Char(string='reference to the model for m2o_reference')

    def _selection_reference_model(self):
        return [('test_search.lesson', None)]


class TestSearchLesson(models.Model):
    _name = 'test_search.lesson'
    _description = 'a lesson of a course (a day typically)'

    name = fields.Char('Name')
    course_id = fields.Many2one('test_search.course')
    attendee_ids = fields.Many2many('test_search.person', context={'active_test': False})
    teacher_id = fields.Many2one('test_search.person')
    teacher_birthdate = fields.Date(related='teacher_id.birthday')
    date = fields.Date()

    def _compute_display_name(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        for record in self:
            if 'special' in self.env.context:
                record.display_name = 'special ' + record.name
            else:
                record.display_name = record.name


class TestSearchPerson(models.Model):
    _name = 'test_search.person'
    _description = 'a person, can be an author, teacher or attendee of a lesson'

    name = fields.Char('Name')
    lesson_ids = fields.Many2many('test_search.lesson')
    employer_id = fields.Many2one('test_search.employer')
    birthday = fields.Date()
    active = fields.Boolean(default=True)

    def _compute_display_name(self):
        """
        use to check that a context has can still have an impact when reading the names of a many2one
        """
        particular = "particular " if 'particular' in self.env.context else ""
        special = " special" if 'special' in self.env.context else ""
        for record in self:
            record.display_name = f"{particular}{record.name}{special}"


class TestSearchEmployer(models.Model):
    _name = 'test_search.employer'
    _description = 'the employer of a person'

    name = fields.Char('Name')
    employee_ids = fields.One2many('test_search.person', 'employer_id')
    all_employee_ids = fields.One2many('test_search.person', 'employer_id', context={'active_test': False})


class TestSearchPersonAccount(models.Model):
    _name = 'test_search.person.account'
    _description = 'an account with credentials for a given person'
    _inherits = {'test_search.person': 'person_id'}

    person_id = fields.Many2one('test_search.person', required=True, ondelete='cascade')
    login = fields.Char()
    activation_date = fields.Date()


class TestSearchViewStrId(models.Model):
    _name = 'test_search.view.str.id'
    _description = 'test_search.view.str.id'
    _auto = False
    _table_query = "SELECT 'hello' AS id, 'test' AS name"

    name = fields.Char()
