from odoo import fields, models


class TestSortCountry(models.Model):
    _name = 'test_sort.country'
    _description = 'Country, ordered by name'
    _order = 'name, id'

    name = fields.Char()


class TestSortCity(models.Model):
    _name = 'test_sort.city'
    _description = 'City, ordered by country then name'
    _order = 'country_id, name, id'

    name = fields.Char()
    country_id = fields.Many2one('test_sort.country')


class TestSortModelActiveField(models.Model):
    _name = 'test_sort.model_active_field'
    _description = 'A model with active field'

    name = fields.Char()
    active = fields.Boolean(default=True)


class TestSortCategory(models.Model):
    _name = 'test_sort.category'
    _description = 'Test ORM Category'
    _order = 'name'
    _parent_store = True
    _parent_name = 'parent'

    name = fields.Char(required=True)
    parent = fields.Many2one('test_sort.category', ondelete='cascade')
    parent_path = fields.Char(index=True)
