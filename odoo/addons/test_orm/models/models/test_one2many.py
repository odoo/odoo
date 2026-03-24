from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TestOne2manyMulti(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_one2many.multi'
    _description = 'Test ORM Multi'

    name = fields.Char(related='partner.name', readonly=True)

    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_one2many.multi.line', 'multi')

    @api.onchange('name')
    def _onchange_name(self):
        for line in self.lines:
            line.name = self.name


class TestOne2manyMultiLine(models.Model):
    _name = 'test_one2many.multi.line'
    _description = 'Test ORM Multi Line'

    multi = fields.Many2one('test_one2many.multi', ondelete='cascade')
    name = fields.Char()


class TestOne2manyCreativeworkEdition(models.Model):
    _name = 'test_one2many.creativework.edition'
    _description = 'Test ORM Creative Work Edition'

    name = fields.Char()
    res_id = fields.Integer(required=True)
    res_model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    res_model = fields.Char(related='res_model_id.model', store=True, readonly=False)


class TestOne2manyCreativeworkBook(models.Model):
    _name = 'test_one2many.creativework.book'
    _description = 'Test ORM Creative Work Book'

    name = fields.Char()
    editions = fields.One2many(
        'test_one2many.creativework.edition', 'res_id', domain=[('res_model', '=', 'test_one2many.creativework.book')],
    )


class TestOne2manyCreativeworkMovie(models.Model):
    _name = 'test_one2many.creativework.movie'
    _description = 'Test ORM Creative Work Movie'

    name = fields.Char()
    editions = fields.One2many(
        'test_one2many.creativework.edition', 'res_id', domain=[('res_model', '=', 'test_one2many.creativework.movie')],
    )


class TestOne2manyField_With_Caps(models.Model):
    _name = 'test_one2many.field_with_caps'
    _description = 'Model with field defined with capital letters'

    pArTneR_321_id = fields.Many2one('res.partner')


class TestOne2manyAttachment(models.Model):
    _name = 'test_one2many.attachment'
    _description = 'Attachment'
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


class TestOne2manyAttachmentHost(models.Model):
    _name = 'test_one2many.attachment.host'
    _description = 'Attachment Host'

    attachment_ids = fields.One2many(
        'test_one2many.attachment', 'res_id', bypass_search_access=True,
        domain=lambda self: [('res_model', '=', self._name)],
    )


class TestOne2manyDiscussion(models.Model):
    _name = 'test_one2many.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    messages = fields.One2many('test_one2many.message', 'discussion', copy=True)


class TestOne2manyMessage(models.Model):
    _name = 'test_one2many.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_one2many.discussion', ondelete='cascade')
    body = fields.Text(index='trigram')


class TestOne2manyModelChildM2o(models.Model):
    _name = 'test_one2many.model_child_m2o'
    _description = 'dummy model with override write and ValidationError'

    name = fields.Char('Name')
    parent_id = fields.Many2one('test_one2many.model_parent_m2o', ondelete='cascade')
    size1 = fields.Integer(compute='_compute_sizes', store=True)
    size2 = fields.Integer(compute='_compute_sizes', store=True)

    @api.depends('parent_id.name')
    def _compute_sizes(self):
        for record in self:
            record.size1 = len(record.parent_id.name)
            record.size2 = len(record.parent_id.name)

    def write(self, vals):
        res = super().write(vals)
        if self.name == 'A':
            msg = 'the first existing child should not be changed when adding a new child to the parent'
            raise ValidationError(msg)
        return res


class TestOne2manyModelParentM2o(models.Model):
    _name = 'test_one2many.model_parent_m2o'
    _description = 'dummy model with multiple childs'

    name = fields.Char('Name')
    child_ids = fields.One2many('test_one2many.model_child_m2o', 'parent_id', string="Children")


class TestOne2manyOrder(models.Model):
    _name = 'test_one2many.order'
    _description = 'test_one2many.order'

    line_ids = fields.One2many('test_one2many.order.line', 'order_id')


class TestOne2manyOrderLine(models.Model):
    _name = 'test_one2many.order.line'
    _description = 'test_one2many.order.line'

    order_id = fields.Many2one('test_one2many.order', required=True, ondelete='cascade')
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
        self = self.union(*reward_lines)  # noqa: PLW0642
        return super().unlink()


class TestOne2manyComputeContainer(models.Model):
    _name = 'test_one2many.compute.container'
    _description = 'test_one2many.compute.container'

    name = fields.Char()
    member_ids = fields.One2many('test_one2many.compute.member', 'container_id')
    member_count = fields.Integer(compute='_compute_member_count', store=True)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)


class TestOne2manyComputeMember(models.Model):
    _name = 'test_one2many.compute.member'
    _description = 'test_one2many.compute.member'

    name = fields.Char()
    container_id = fields.Many2one('test_one2many.compute.container', compute='_compute_container', store=True)

    @api.depends('name')
    def _compute_container(self):
        container = self.env['test_one2many.compute.container']
        for member in self:
            member.container_id = container.search([('name', '=', member.name)], limit=1)


class TestOne2manyTeam(models.Model):
    _name = 'test_one2many.team'
    _description = 'Odoo Team'

    name = fields.Char()
    parent_id = fields.Many2one('test_one2many.team')
    member_ids = fields.One2many('test_one2many.team.member', 'team_id')


class TestOne2manyTeamMember(models.Model):
    _name = 'test_one2many.team.member'
    _description = 'Odoo Developer'

    name = fields.Char('Name')
    team_id = fields.Many2one('test_one2many.team')
    parent_id = fields.Many2one('test_one2many.team', related='team_id.parent_id')


class TestOne2manyUnsearchableO2m(models.Model):
    _name = 'test_one2many.unsearchable.o2m'
    _description = 'Test non-stored unsearchable o2m'

    name = fields.Char('Name')
    stored_parent_id = fields.Many2one('test_one2many.unsearchable.o2m', store=True)
    parent_id = fields.Many2one('test_one2many.unsearchable.o2m', store=False, compute="_compute_parent_id")
    child_ids = fields.One2many('test_one2many.unsearchable.o2m', 'parent_id')

    @api.depends('stored_parent_id')
    def _compute_parent_id(self):
        for r in self:
            r.parent_id = r.stored_parent_id


class TestOne2manyComputedInverseOne2many(models.Model):
    _name = 'test_one2many.computed_inverse_one2many'
    _description = "A computed/inverse o2m, subset of a main one"

    name = fields.Char()
    all_line_ids = fields.One2many('test_one2many.computed_inverse_one2many_line', 'parent_id')
    low_priority_line_ids = fields.One2many('test_one2many.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')
    high_priority_line_ids = fields.One2many('test_one2many.computed_inverse_one2many_line', compute='_compute_priority_line_ids', inverse='_inverse_line_ids')

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
    _name = 'test_one2many.computed_inverse_one2many_line'
    _description = "Line of a computed/inverse one2many"

    name = fields.Char()
    priority = fields.Integer()
    parent_id = fields.Many2one('test_one2many.computed_inverse_one2many')
