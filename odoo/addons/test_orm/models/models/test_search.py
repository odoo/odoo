from odoo import api, fields, models
from odoo.tools import SQL


class TestSearchMulti(models.Model):
    """ Model for testing multiple onchange methods in cascade that modify a
        one2many field several times.
    """
    _name = 'test_search.multi'
    _description = 'Test ORM Multi'

    name = fields.Char(related='partner.name', readonly=True)
    partner = fields.Many2one('res.partner')
    lines = fields.One2many('test_search.multi.line', 'multi')
    tags = fields.Many2many('test_search.multi.tag', domain=[('name', 'ilike', 'a')])


class TestSearchMultiLine(models.Model):
    _name = 'test_search.multi.line'
    _description = 'Test ORM Multi Line'

    multi = fields.Many2one('test_search.multi', ondelete='cascade')
    name = fields.Char()


class TestSearchMultiTag(models.Model):
    _name = 'test_search.multi.tag'
    _description = 'Test ORM Multi Tag'

    name = fields.Char()


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

    foo_names = fields.Char(related='foo_ids.name', related_sudo=False, string="Foo Names")
    foo_names_sudo = fields.Char(related='foo_ids.name', related_sudo=True, string="Foo Names Sudo")

    bar_names = fields.Char(related='bar_ids.name', related_sudo=False, string="Bar Names")
    bar_names_sudo = fields.Char(related='bar_ids.name', related_sudo=True, string="Bar Names Sudo")


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

    quantity = fields.Integer(compute='_compute_quantity', store=True)
    tag_id = fields.Many2one('test_search.multi.tag')
    tag_repeat = fields.Integer()

    # This field can fool the ORM during onchanges!  When editing a payment
    # record, modified fields are assigned to the parent record.  When
    # determining the dependent records, the ORM looks for the payments related
    # to this record by the field `move_id`.  As this field is an inverse of
    # `move_id`, it uses it.  If that field was not initialized properly, the
    # ORM determines its value to be... empty (instead of the payment record.)
    payment_ids = fields.One2many('test_search.payment', 'move_id')


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


class TestSearchLesson(models.Model):
    _name = 'test_search.lesson'
    _description = 'a lesson of a course (a day typically)'

    attendee_ids = fields.Many2many('test_search.person', context={'active_test': False})
    teacher_id = fields.Many2one('test_search.person')
    teacher_birthdate = fields.Date(related='teacher_id.birthday')


class TestSearchPerson(models.Model):
    _name = 'test_search.person'
    _description = 'a person, can be an author, teacher or attendee of a lesson'

    name = fields.Char('Name')
    birthday = fields.Date()


class TestSearchPersonAccount(models.Model):
    _name = 'test_search.person.account'
    _description = 'an account with credentials for a given person'
    _inherits = {'test_search.person': 'person_id'}

    person_id = fields.Many2one('test_search.person', required=True, ondelete='cascade')
    activation_date = fields.Date()


class TestSearchViewStrId(models.Model):
    _name = 'test_search.view.str.id'
    _description = 'test_search.view.str.id'
    _auto = False
    _table_query = "SELECT 'hello' AS id, 'test' AS name"

    name = fields.Char()
