from odoo import api, fields, models


class TestOrmCrew(models.Model):
    _name = 'test_orm.crew'
    _description = 'All yaaaaaarrrrr by ship'
    _table = 'test_orm_crew'

    # this actually represents the union of two relations pirate/ship and
    # prisoner/ship, where some of the many2one fields can be NULL
    pirate_id = fields.Many2one('test_orm.pirate')
    prisoner_id = fields.Many2one('test_orm.prisoner')
    ship_id = fields.Many2one('test_orm.ship')


class TestOrmShip(models.Model):
    _name = 'test_orm.ship'
    _description = 'Yaaaarrr machine'

    name = fields.Char('Name')
    pirate_ids = fields.Many2many('test_orm.pirate', 'test_orm_crew', 'ship_id', 'pirate_id')
    prisoner_ids = fields.Many2many('test_orm.prisoner', 'test_orm_crew', 'ship_id', 'prisoner_id')


class TestOrmPirate(models.Model):
    _name = 'test_orm.pirate'
    _description = 'Yaaarrr'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_orm.ship', 'test_orm_crew', 'pirate_id', 'ship_id')


class TestOrmPrisoner(models.Model):
    _name = 'test_orm.prisoner'
    _description = 'Yaaarrr minions'

    name = fields.Char('Name')
    ship_ids = fields.Many2many('test_orm.ship', 'test_orm_crew', 'prisoner_id', 'ship_id')


class TestOrmAttachment(models.Model):
    _name = 'test_orm.attachment'
    _description = 'Attachment'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    name = fields.Char(compute='_compute_name', compute_sudo=True, store=True)

    @api.depends('res_model', 'res_id')
    def _compute_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).display_name

    # override those methods for many2many search
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        return super()._search(domain, offset, limit, order, active_test=active_test, bypass_access=bypass_access)

    def _check_access(self, operation):
        return super()._check_access(operation)

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


class TestOrmAttachmentHost(models.Model):
    _name = 'test_orm.attachment.host'
    _description = 'Attachment Host'

    attachment_ids = fields.One2many(
        'test_orm.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    m2m_attachment_ids = fields.Many2many(
        'test_orm.attachment', bypass_search_access=True,
    )

    real_binary = fields.Binary(attachment=True)
    real_attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )
    real_m2m_attachment_ids = fields.Many2many(
        'ir.attachment', bypass_search_access=True,
    )


class TestOrmMulti(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_orm.multi'
    _description = 'Test ORM Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_orm.multi.line', 'multi')
    partners = fields.One2many(related='partner.child_ids')
    tags = fields.Many2many('test_orm.multi.tag', domain=[('name', 'ilike', 'a')])

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


class TestOrmMultiLine(models.Model):
    _name = 'test_orm.multi.line'
    _description = 'Test ORM Multi Line'

    multi = fields.Many2one('test_orm.multi', ondelete='cascade')
    name = fields.Char()
    partner = fields.Many2one(related='multi.partner', store=True)
    tags = fields.Many2many('test_orm.multi.tag')


class TestOrmMultiLine2(models.Model):
    _name = 'test_orm.multi.line2'
    _inherit = ['test_orm.multi.line']
    _description = 'Test ORM Multi Line 2'


class TestOrmMultiTag(models.Model):
    _name = 'test_orm.multi.tag'
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


class TestOrmCreativeworkEdition(models.Model):
    _name = 'test_orm.creativework.edition'
    _description = 'Test ORM Creative Work Edition'

    name = fields.Char()
    res_id = fields.Integer(required=True)
    res_model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    res_model = fields.Char(related='res_model_id.model', store=True, readonly=False)


class TestOrmCreativeworkBook(models.Model):
    _name = 'test_orm.creativework.book'
    _description = 'Test ORM Creative Work Book'

    name = fields.Char()
    editions = fields.One2many(
        'test_orm.creativework.edition', 'res_id', domain=[('res_model', '=', 'test_orm.creativework.book')],
    )


class TestOrmCreativeworkMovie(models.Model):
    _name = 'test_orm.creativework.movie'
    _description = 'Test ORM Creative Work Movie'

    name = fields.Char()
    editions = fields.One2many(
        'test_orm.creativework.edition', 'res_id', domain=[('res_model', '=', 'test_orm.creativework.movie')],
    )


class TestOrmField_With_Caps(models.Model):
    _name = 'test_orm.field_with_caps'
    _description = 'Model with field defined with capital letters'

    pArTneR_321_id = fields.Many2one('res.partner')


class TestOrmModel_Child_M2o(models.Model):
    _name = 'test_orm.model_child_m2o'
    _description = 'dummy model with override write and ValidationError'

    name = fields.Char('Name')
    parent_id = fields.Many2one('test_orm.model_parent_m2o', ondelete='cascade')
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


class TestOrmModel_Parent_M2o(models.Model):
    _name = 'test_orm.model_parent_m2o'
    _description = 'dummy model with multiple childs'

    name = fields.Char('Name')
    child_ids = fields.One2many('test_orm.model_child_m2o', 'parent_id', string="Children")
    cost = fields.Integer(compute='_compute_cost', store=True)

    @api.depends('child_ids.cost')
    def _compute_cost(self):
        for record in self:
            record.cost = sum(child.cost for child in record.child_ids)


class TestOrmOrder(models.Model):
    _name = 'test_orm.order'
    _description = 'test_orm.order'

    line_ids = fields.One2many('test_orm.order.line', 'order_id')
    line_short_field_name = fields.Integer(index=True)


class TestOrmOrderLine(models.Model):
    _name = 'test_orm.order.line'
    _description = 'test_orm.order.line'

    order_id = fields.Many2one('test_orm.order', required=True, ondelete='cascade')
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


class TestOrmComputeContainer(models.Model):
    _name = 'test_orm.compute.container'
    _description = 'test_orm.compute.container'

    name = fields.Char()
    name_translated = fields.Char(translate=True)
    member_ids = fields.One2many('test_orm.compute.member', 'container_id')
    member_count = fields.Integer(compute='_compute_member_count', store=True)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)


class TestOrmComputeMember(models.Model):
    _name = 'test_orm.compute.member'
    _description = 'test_orm.compute.member'

    name = fields.Char()
    container_id = fields.Many2one('test_orm.compute.container', compute='_compute_container', store=True)
    container_super_id = fields.Many2one(
        'test_orm.compute.container', string='Container For SUPERUSER',
    )
    container_context_id = fields.Many2one(
        'test_orm.compute.container',
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
        container = self.env['test_orm.compute.container']
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


class TestOrmTeam(models.Model):
    _name = 'test_orm.team'
    _description = 'Odoo Team'

    name = fields.Char()
    parent_id = fields.Many2one('test_orm.team')
    member_ids = fields.One2many('test_orm.team.member', 'team_id')


class TestOrmTeamMember(models.Model):
    _name = 'test_orm.team.member'
    _description = 'Odoo Developer'

    name = fields.Char('Name')
    team_id = fields.Many2one('test_orm.team')
    parent_id = fields.Many2one('test_orm.team', related='team_id.parent_id')


class TestOrmUnsearchableO2m(models.Model):
    _name = 'test_orm.unsearchable.o2m'
    _description = 'Test non-stored unsearchable o2m'

    name = fields.Char('Name')
    stored_parent_id = fields.Many2one('test_orm.unsearchable.o2m', store=True)
    parent_id = fields.Many2one('test_orm.unsearchable.o2m', store=False, compute="_compute_parent_id")
    child_ids = fields.One2many('test_orm.unsearchable.o2m', 'parent_id')

    @api.depends('stored_parent_id')
    def _compute_parent_id(self):
        for r in self:
            r.parent_id = r.stored_parent_id


class TestOrmComputedInverseOne2many(models.Model):
    _name = 'test_orm.computed_inverse_one2many'
    _description = "A computed/inverse o2m, subset of a main one"

    name = fields.Char()
    all_line_ids = fields.One2many('test_orm.computed_inverse_one2many_line', 'parent_id')
    low_priority_line_ids = fields.One2many('test_orm.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')
    high_priority_line_ids = fields.One2many('test_orm.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')

    @api.depends('all_line_ids')
    def _compute_priority_line_ids(self):
        for record in self:
            low_lines = record.all_line_ids.filtered(lambda line: line.priority < 4)
            record.low_priority_line_ids = low_lines
            record.high_priority_line_ids = record.all_line_ids - low_lines

    def _inverse_line_ids(self):
        for record in self:
            record.all_line_ids = record.low_priority_line_ids | record.high_priority_line_ids


class TesOrmComputedInverseOne2manyLine(models.Model):
    _name = 'test_orm.computed_inverse_one2many_line'
    _description = "Line of a computed/inverse one2many"

    name = fields.Char()
    priority = fields.Integer()
    parent_id = fields.Many2one('test_orm.computed_inverse_one2many')


class TestOrmModel_A(models.Model):
    _name = 'test_orm.model_a'
    _description = 'Model A'

    name = fields.Char()
    a_restricted_b_ids = fields.Many2many('test_orm.model_b', relation='rel_model_a_model_b_1')
    b_restricted_b_ids = fields.Many2many('test_orm.model_b', relation='rel_model_a_model_b_2', ondelete='restrict')


class TestOrmModel_B(models.Model):
    _name = 'test_orm.model_b'
    _description = 'Model B'

    name = fields.Char()
    a_restricted_a_ids = fields.Many2many('test_orm.model_a', relation='rel_model_a_model_b_1', ondelete='restrict')
    b_restricted_a_ids = fields.Many2many('test_orm.model_a', relation='rel_model_a_model_b_2')


class TestOrmReq_M2o(models.Model):
    _name = 'test_orm.req_m2o'
    _description = 'Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='cascade')
    bar = fields.Many2one('res.country', required=True)


class TestOrmReq_M2o_Transient(models.TransientModel):
    _name = 'test_orm.req_m2o_transient'
    _description = 'Transient Model with Required Many2one'

    foo = fields.Many2one('res.currency', required=True, ondelete='restrict')
    bar = fields.Many2one('res.country', required=True)


class TestOrmModel_Many2one_Reference(models.Model):
    _name = 'test_orm.model_many2one_reference'
    _description = 'dummy m2oref model'

    res_model = fields.Char('Resource Model')
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model')
    const = fields.Boolean(default=True)


class TestOrmInverse_M2o_Ref(models.Model):
    _name = 'test_orm.inverse_m2o_ref'
    _description = 'dummy m2oref inverse model'

    model_ids = fields.One2many(
        'test_orm.model_many2one_reference', 'res_id',
        string="Models", domain=[('const', '=', True)])
    model_ids_count = fields.Integer("Count", compute='_compute_model_ids_count')
    model_computed_ids = fields.One2many(
        'test_orm.model_many2one_reference',
        string="Models Computed",
        compute='_compute_model_computed_ids',
    )

    @api.depends('model_ids')
    def _compute_model_ids_count(self):
        for rec in self:
            rec.model_ids_count = len(rec.model_ids)

    def _compute_model_computed_ids(self):
        self.model_computed_ids = []
