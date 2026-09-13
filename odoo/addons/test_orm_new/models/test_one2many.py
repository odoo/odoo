import itertools


from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class TestOrmOne2manyMulti(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_orm.one2many.multi'
    _description = 'Test ORM One2many Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('test_orm.partner')
    lines = fields.One2many('test_orm.one2many.multi_line', 'multi')
    partners = fields.One2many(related='partner.child_ids')
    tags = fields.Many2many('test_orm.one2many.multi_tag', domain=[('name', 'ilike', 'a')])


class TestOrmOne2manyMultiLine(models.Model):
    _name = 'test_orm.one2many.multi_line'
    _description = 'Test ORM One2many Multi Line'

    multi = fields.Many2one('test_orm.one2many.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one(related='multi.partner', store=True)
    tags = fields.Many2many('test_orm.one2many.multi_tag')


class TestOrmOne2manyMultiTag(models.Model):
    _name = 'test_orm.one2many.multi_tag'
    _description = 'Test ORM One2many Multi Tag'

    name = fields.Char()

    @api.depends('name')
    @api.depends_context('special_tag')
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if name and self.env.context.get('special_tag'):
                name += "!"
            record.display_name = name or ""


class TestOrmOne2manyCreativeworkEdition(models.Model):
    _name = 'test_orm.one2many.creativework_edition'
    _description = 'Test ORM One2many Creative Work Edition'

    name = fields.Char()
    res_id = fields.Integer(required=True)
    res_model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    res_model = fields.Char(related='res_model_id.model', store=True, readonly=False)


class TestOrmOne2manyCreativeworkBook(models.Model):
    _name = 'test_orm.one2many.creativework_book'
    _description = 'Test ORM One2many Creative Work Book'

    name = fields.Char()
    editions = fields.One2many(
        'test_orm.one2many.creativework_edition', 'res_id', domain=[('res_model', '=', 'test_orm.creativework_book')],
    )


class TestOrmOne2manyCreativeworkMovie(models.Model):
    _name = 'test_orm.one2many.creativework_movie'
    _description = 'Test ORM One2many Creative Work Movie'

    name = fields.Char()
    editions = fields.One2many(
        'test_orm.one2many.creativework_edition', 'res_id', domain=[('res_model', '=', 'test_orm.one2many.creativework_movie')],
    )


class TestOrmOne2manyFieldWithCaps(models.Model):
    _name = 'test_orm.one2many.field_with_caps'
    _description = 'Test ORM One2many Field With Caps'

    pArTneR_321_id = fields.Many2one('res.partner')


class TestOrmOne2manyAttachment(models.Model):
    _name = 'test_orm.one2many.attachment'
    _description = 'Test ORM One2many Attachment'
    _access_domain_heavy = True

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
            return None
        comodel = self.env[self.res_model]
        if 'res_id' in fnames and 'attachment_ids' in comodel:
            record = comodel.browse(self.res_id)
            record.invalidate_recordset(['attachment_ids'])
            record.modified(['attachment_ids'])
        return super().modified(fnames, *args, **kwargs)


class TestOrmOne2manyAttachmentHost(models.Model):
    _name = 'test_orm.one2many.attachment_host'
    _description = 'Test ORM One2many Attachment Host'

    attachment_ids = fields.One2many(
        'test_orm.one2many.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    m2m_attachment_ids = fields.Many2many(
        'test_orm.one2many.attachment',
        'test_orm_o2m_attachment_host_rel',
        bypass_search_access=True,
    )

    real_binary = fields.Binary(attachment=True)
    real_attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    real_m2m_attachment_ids = fields.Many2many(
        'ir.attachment',
        'test_orm_o2m_real_attachment_host_rel',
        bypass_search_access=True,
    )


class TestOrmOne2manyModelChildM2o(models.Model):
    _name = 'test_orm.one2many.model_child_m2o'
    _description = 'Test ORM One2many Model Child m2o'

    name = fields.Char('Name')
    parent_id = fields.Many2one('test_orm.one2many.model_parent_m2o', ondelete='cascade')
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
        res = super().write(vals)
        if self.name == 'A':
            msg = 'the first existing child should not be changed when adding a new child to the parent'
            raise ValidationError(msg)
        return res


class TestOrmOne2manyModelParentM2o(models.Model):
    _name = 'test_orm.one2many.model_parent_m2o'
    _description = 'Test ORM One2many Model Parent m2o'

    name = fields.Char('Name')
    child_ids = fields.One2many('test_orm.one2many.model_child_m2o', 'parent_id', string="Children")
    cost = fields.Integer(compute='_compute_cost', store=True)

    @api.depends('child_ids.cost')
    def _compute_cost(self):
        for record in self:
            record.cost = sum(child.cost for child in record.child_ids)


class TestOrmOne2manyOrder(models.Model):
    _name = 'test_orm.one2many.order'
    _description = 'Test ORM One2many Order'

    line_ids = fields.One2many('test_orm.one2many.order_line', 'order_id')
    line_short_field_name = fields.Integer(index=True)


class TestOrmOne2manyOrderLine(models.Model):
    _name = 'test_orm.one2many.order_line'
    _description = 'test_orm.one2many.order_line'

    order_id = fields.Many2one('test_orm.one2many.order', required=True, ondelete='cascade')
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
        self |= self.browse().union(reward_lines)  # noqa: PLW0642
        return super().unlink()


class TestOrmOne2manyComputeContainer(models.Model):
    _name = 'test_orm.one2many.compute_container'
    _description = 'Test ORM One2many Compute Container'

    name = fields.Char()
    name_translated = fields.Char(translate=True)
    member_ids = fields.One2many('test_orm.one2many.compute_member', 'container_id')
    member_count = fields.Integer(compute='_compute_member_count', store=True)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)


class TestOrmOne2manyComputeMember(models.Model):
    _name = 'test_orm.one2many.compute_member'
    _description = 'Test ORM One2many Compute Member'

    name = fields.Char()
    container_id = fields.Many2one('test_orm.one2many.compute_container', compute='_compute_container', store=True)
    container_super_id = fields.Many2one(
        'test_orm.one2many.compute_container', string='Container For SUPERUSER',
    )
    container_context_id = fields.Many2one(
        'test_orm.one2many.compute_container',
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
        container = self.env['test_orm.one2many.compute_container']
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


class TestOrmOne2manyTeam(models.Model):
    _name = 'test_orm.one2many.team'
    _description = 'Test ORM One2many Team'

    name = fields.Char()
    parent_id = fields.Many2one('test_orm.one2many.team')
    member_ids = fields.One2many('test_orm.one2many.team_member', 'team_id')


class TestOrmOne2manyTeamMember(models.Model):
    _name = 'test_orm.one2many.team_member'
    _description = 'Test ORM One2man Team Member'

    name = fields.Char('Name')
    team_id = fields.Many2one('test_orm.one2many.team')
    parent_id = fields.Many2one('test_orm.one2many.team', related='team_id.parent_id')


class TestOrmOne2manyUnsearchableO2m(models.Model):
    _name = 'test_orm.one2many.unsearchable_o2m'
    _description = 'Test ORM One2many Unsearchable o2m'

    name = fields.Char('Name')
    stored_parent_id = fields.Many2one('test_orm.one2many.unsearchable_o2m', store=True)
    parent_id = fields.Many2one('test_orm.one2many.unsearchable_o2m', store=False, compute="_compute_parent_id")
    child_ids = fields.One2many('test_orm.one2many.unsearchable_o2m', 'parent_id')

    @api.depends('stored_parent_id')
    def _compute_parent_id(self):
        for r in self:
            r.parent_id = r.stored_parent_id


class TestOrmOne2manyComputedInverseOne2many(models.Model):
    _name = 'test_orm.one2many.computed_inverse_one2many'
    _description = "Test ORM One2many Computed Inverse One2many"

    name = fields.Char()
    all_line_ids = fields.One2many('test_orm.one2many.computed_inverse_one2many_line', 'parent_id')
    low_priority_line_ids = fields.One2many('test_orm.one2many.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')
    high_priority_line_ids = fields.One2many('test_orm.one2many.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')

    @api.depends('all_line_ids')
    def _compute_priority_line_ids(self):
        for record in self:
            low_lines = record.all_line_ids.filtered(lambda line: line.priority < 4)
            record.low_priority_line_ids = low_lines
            record.high_priority_line_ids = record.all_line_ids - low_lines

    def _inverse_line_ids(self):
        for record in self:
            record.all_line_ids = record.low_priority_line_ids | record.high_priority_line_ids


class TestOrmOne2manyComputedInverseOne2manyLine(models.Model):
    _name = 'test_orm.one2many.computed_inverse_one2many_line'
    _description = "Test ORM One2many Computed Inverse One2many Line"

    name = fields.Char()
    priority = fields.Integer()
    parent_id = fields.Many2one('test_orm.one2many.computed_inverse_one2many')


class TestOrmOne2manyCategory(models.Model):
    _name = 'test_orm.one2many.category'
    _description = 'Test ORM One2many Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')
    parent = fields.Many2one('test_orm.one2many.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
    depth = fields.Integer(compute="_compute_depth")
    root_categ = fields.Many2one('test_orm.one2many.category', compute='_compute_root_categ')
    display_name = fields.Char(
        inverse='_inverse_display_name',
        recursive=True,
    )
    dummy = fields.Char(store=False)
    discussions = fields.Many2many('test_orm.one2many.discussion', 'test_orm_discussion_category',
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


class TestOrmOne2manyDiscussion(models.Model):
    _name = 'test_orm.one2many.discussion'
    _description = 'Test ORM One2many Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_orm.one2many.category',
        'test_orm_discussion_category', 'discussion', 'category')
    participants = fields.Many2many('res.users', context={'active_test': False})
    messages = fields.One2many('test_orm.one2many.message', 'discussion', copy=True)
    message_concat = fields.Text(string='Message concatenate')
    important_messages = fields.One2many('test_orm.one2many.message', 'discussion',
                                         domain=[('important', '=', True)])
    very_important_messages = fields.One2many(
        'test_orm.one2many.message', 'discussion',
        domain=lambda self: self._domain_very_important())
    emails = fields.One2many('test_orm.one2many.email_message', 'discussion')
    important_emails = fields.One2many('test_orm.one2many.email_message', 'discussion',
                                       domain=[('important', '=', True)])

    history = fields.Json('History', default={'delete_messages': []})
    attributes_definition = fields.PropertiesDefinition('Message Properties')  # see message@attributes

    def _domain_very_important(self):
        """Ensure computed O2M domains work as expected."""
        return [("important", "=", True)]


class TestOrmOne2manyMessage(models.Model):
    _name = 'test_orm.one2many.message'
    _description = 'Test ORM One2many Message'

    discussion = fields.Many2one('test_orm.one2many.discussion', ondelete='cascade')
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
    has_important_sibling = fields.Boolean(compute='_compute_has_important_sibling', search='_search_has_important_sibling')

    attributes = fields.Properties(
        string='Discussion Properties',
        definition='discussion.attributes_definition',
    )

    @api.depends('discussion.messages.important')
    def _compute_has_important_sibling(self):
        for record in self:
            siblings = record.discussion.with_context(active_test=False).messages - record
            record.has_important_sibling = any(siblings.mapped('important'))

    def _search_has_important_sibling(self, operator, value):
        if operator != 'in':
            return NotImplemented
        # not entirely correct, but sufficent for tests
        return [('discussion.messages.important', '=', True)]

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
        rows = self.env.execute_query(SQL(
            'SELECT id FROM %s WHERE char_length("body") %s %s',
            SQL.identifier(self._table),
            SQL(operator),  # pylint: disable=sql-injection
            value,
        ))
        ids = [t[0] for t in rows]
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


class TestOrmOne2manyEmailMessage(models.Model):
    _name = 'test_orm.one2many.email_message'
    _description = 'Test ORM One2many Email Message'
    _inherits = {'test_orm.one2many.message': 'message'}
    _inherit = 'properties.base.definition.mixin'

    message = fields.Many2one('test_orm.one2many.message', 'Message',
                              required=True, ondelete='cascade')
    email_to = fields.Char('To')
    active = fields.Boolean('Active Message', related='message.active', store=True, related_sudo=False)
