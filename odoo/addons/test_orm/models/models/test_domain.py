from odoo import api, fields, models


class TestDomainIndexedTranslation(models.Model):
    _name = 'test_domain.indexed_translation'
    _description = 'A model to indexed translated fields'

    name = fields.Text('Name trigram', translate=True, index='trigram')


class TestDomainAnyParent(models.Model):
    _name = 'test_domain.any.parent'
    _description = 'Any Parent'

    name = fields.Char()
    child_ids = fields.One2many('test_domain.any.child', 'parent_id')


class TestDomainAnyChild(models.Model):
    _name = 'test_domain.any.child'
    _description = 'Any Child'
    _inherits = {
        'test_domain.any.parent': 'parent_id',
    }

    parent_id = fields.Many2one('test_domain.any.parent', required=True, ondelete='cascade')
    link_sibling_id = fields.Many2one('test_domain.any.child')
    quantity = fields.Integer()
    tag_ids = fields.Many2many('test_domain.any.tag')


class TestDomainAnyTag(models.Model):
    _name = 'test_domain.any.tag'
    _description = 'Any tag'

    name = fields.Char()
    child_ids = fields.Many2many('test_domain.any.child')


class TestDomainModelActiveField(models.Model):
    _name = 'test_domain.model_active_field'
    _description = 'A model with active field'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('test_domain.model_active_field')


class TestDomainFoo(models.Model):
    _name = 'test_domain.foo'
    _description = 'Test ORM Foo'

    name = fields.Char()
    value1 = fields.Integer(change_default=True)
    value2 = fields.Integer()
    text = fields.Char(trim=False)


class TestDomainBar(models.Model):
    _name = 'test_domain.bar'
    _description = 'Test ORM Bar'

    name = fields.Char()
    foo = fields.Many2one('test_domain.foo', compute='_compute_foo', search='_search_foo')

    @api.depends('name')
    def _compute_foo(self):
        for bar in self:
            bar.foo = self.env['test_domain.foo'].search([('name', '=', bar.name)], limit=1)

    def _search_foo(self, operator, value):
        if operator not in ('in', 'any'):
            return NotImplemented
        records = self.env['test_domain.foo'].browse(value)
        return [('name', 'in', records.mapped('name'))]


class TestDomainCategory(models.Model):
    _name = 'test_domain.category'
    _description = 'Test ORM Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    parent = fields.Many2one('test_domain.category', ondelete='cascade')
    parent_path = fields.Char(index=True)


class TestDomainDiscussion(models.Model):
    _name = 'test_domain.discussion'
    _description = 'Test ORM Discussion'

    name = fields.Char(string='Title', required=True, help="Description of discussion.")
    moderator = fields.Many2one('res.users')
    categories = fields.Many2many('test_domain.category', 'test_domain_discussion_category', 'discussion', 'category')
    messages = fields.One2many('test_domain.message', 'discussion', copy=True)


class TestDomainMessage(models.Model):
    _name = 'test_domain.message'
    _description = 'Test ORM Message'

    discussion = fields.Many2one('test_domain.discussion', ondelete='cascade')
    body = fields.Text(index='trigram')
    name = fields.Char(string='Title', compute='_compute_name', store=True)
    important = fields.Boolean()
    active = fields.Boolean(default=True)
