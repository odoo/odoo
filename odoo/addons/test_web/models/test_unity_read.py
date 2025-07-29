import itertools

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class TestWebCourse(models.Model):
    _name = 'test_web.course'
    _description = 'a course'

    name = fields.Char('Name')
    lesson_ids = fields.One2many('test_web.lesson', 'course_id')
    author_id = fields.Many2one('test_web.person')
    private_field = fields.Char(groups="base.group_no_one")
    reference = fields.Reference(string='reference to lesson', selection='_selection_reference_model')
    m2o_reference_id = fields.Many2oneReference(string='reference to lesson too', model_field='m2o_reference_model')
    m2o_reference_model = fields.Char(string='reference to the model for m2o_reference')

    def _selection_reference_model(self):
        return [('test_web.lesson', None)]


class TestWebLesson(models.Model):
    _name = 'test_web.lesson'
    _description = 'a lesson of a course (a day typically)'

    name = fields.Char('Name')
    course_id = fields.Many2one('test_web.course')
    attendee_ids = fields.Many2many('test_web.person', context={'active_test': False})
    teacher_id = fields.Many2one('test_web.person')
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


class TestWebPerson(models.Model):
    _name = 'test_web.person'
    _description = 'a person, can be an author, teacher or attendee of a lesson'

    name = fields.Char('Name')
    lesson_ids = fields.Many2many('test_web.lesson')
    employer_id = fields.Many2one('test_web.employer')
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


class TestWebEmployer(models.Model):
    _name = 'test_web.employer'
    _description = 'the employer of a person'

    name = fields.Char('Name')
    employee_ids = fields.One2many('test_web.person', 'employer_id')
    all_employee_ids = fields.One2many('test_web.person', 'employer_id', context={'active_test': False})


class TestWebPersonAccount(models.Model):
    _name = 'test_web.person.account'
    _description = 'an account with credentials for a given person'
    _inherits = {'test_web.person': 'person_id'}

    person_id = fields.Many2one('test_web.person', required=True, ondelete='cascade')
    login = fields.Char()
    activation_date = fields.Date()


class TestWebCategory(models.Model):
    _name = 'test_web.category'
    _description = 'Test Web Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_web.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one('test_web.category', compute='_compute_root_categ')
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_web.discussion', 'test_web_discussion_category',
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


class TestWebDiscussion(models.Model):
    _name = 'test_web.discussion'
    _description = 'Test Web Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_web.category',
        'test_web_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_web.message', 'discussion', copy=True)
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_web.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_web.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_web.emailmessage', 'discussion')
    important_emails = fields.One2many('test_web.emailmessage', 'discussion',
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


class TestWebMessage(models.Model):
    _name = 'test_web.message'
    _description = 'Test OWeb Message'

    discussion = fields.Many2one('test_web.discussion', ondelete='cascade')
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


class TestWebEmailmessage(models.Model):
    _name = 'test_web.emailmessage'
    _description = 'Test ORM Email Message'
    _inherits = {'test_web.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_web.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')
    active = fields.Boolean('Active Message', related='message.active', store=True, related_sudo=False)


class TestWebPartner(models.Model):
    """
    Simplified model for partners. Having a specific model avoids all the
    overrides from other modules that may change which fields are being read,
    how many queries it takes to use that model, etc.
    """
    _name = 'test_web.partner'
    _description = 'Discussion Partner'

    name = fields.Char(string='Name')
