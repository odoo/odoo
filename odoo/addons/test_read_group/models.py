from odoo import api, fields, models
from odoo.tools import SQL


class Test_Read_GroupOn_Date(models.Model):
    _name = "test_read_group.on_date"
    _description = "Group Test Read On Date"

    date = fields.Date(string="Date")
    value = fields.Integer(string="Value")


class Test_Read_GroupAggregateBoolean(models.Model):
    _name = "test_read_group.aggregate.boolean"
    _description = "Group Test Read Boolean Aggregate"
    _order = "key DESC"

    key = fields.Integer()
    bool_and = fields.Boolean(
        default=False,
        aggregator="bool_and",
    )
    bool_or = fields.Boolean(
        default=False,
        aggregator="bool_or",
    )
    bool_array = fields.Boolean(
        default=False,
        aggregator="array_agg",
    )


class TestReadGroupAggregateMonetaryRelated(models.Model):
    _name = "test_read_group.aggregate.monetary.related"
    _description = "To test related currency fields in Monetary aggregates"

    stored_currency_id = fields.Many2one(comodel_name="res.currency")
    non_stored_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_non_stored_currency_id",
        store=False,
    )

    @api.depends()
    def _compute_non_stored_currency_id(self):
        for record in self:
            record.non_stored_currency_id = self.env.ref("base.EUR")


class Test_Read_GroupAggregateMonetary(models.Model):
    _name = "test_read_group.aggregate.monetary"
    _description = "Group Test Read Monetary Aggregate"

    name = fields.Char()
    related_model_id = fields.Many2one(
        comodel_name="test_read_group.aggregate.monetary.related"
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
    )
    related_stored_currency_id = fields.Many2one(
        related="related_model_id.stored_currency_id"
    )
    related_non_stored_currency_id = fields.Many2one(
        related="related_model_id.non_stored_currency_id"
    )

    total_in_currency_id = fields.Monetary(
        currency_field="currency_id",
    )
    total_in_related_stored_currency_id = fields.Monetary(
        currency_field="related_stored_currency_id"
    )
    total_in_related_non_stored_currency_id = fields.Monetary(
        currency_field="related_non_stored_currency_id"
    )
    total_twice = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_total_twice",
    )

    @api.depends("total_in_currency_id")
    def _compute_total_twice(self):
        for record in self:
            record.total_twice = record.total_in_currency_id * 2


class Test_Read_GroupAggregate(models.Model):
    _name = "test_read_group.aggregate"
    _order = "id"
    _description = "Group Test Aggregate"

    key = fields.Integer()
    value = fields.Integer(string="Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one(comodel_name="res.partner")
    display_name = fields.Char(store=True)
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_customer_id",
        group_by_field="partner_id",
    )

    @api.depends("partner_id")
    def _compute_customer_id(self):
        for record in self:
            record.customer_id = record.partner_id


SELECTION = [("c", "C"), ("b", "B"), ("a", "A")]


class Test_Read_GroupOn_Selection(models.Model):
    _name = "test_read_group.on_selection"
    _description = "Group Test Read On Selection"

    state = fields.Selection(
        selection=[("a", "A"), ("b", "B")],
        group_expand="_expand_states",
    )
    static_expand = fields.Selection(
        selection=SELECTION,
        group_expand=True,
    )
    dynamic_expand = fields.Selection(
        selection=lambda self: SELECTION,
        group_expand=True,
    )
    no_expand = fields.Selection(selection=SELECTION)
    value = fields.Integer()

    def _expand_states(self, states, domain):
        return [key for key, val in self._fields["state"].selection]


class Test_Read_GroupFill_Temporal(models.Model):
    _name = "test_read_group.fill_temporal"
    _description = "Group Test Fill Temporal"

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class Test_Read_GroupOrder(models.Model):
    _name = "test_read_group.order"
    _description = "Sales order"

    line_ids = fields.One2many(
        comodel_name="test_read_group.order.line",
        inverse_name="order_id",
    )
    date = fields.Date()
    company_dependent_name = fields.Char(company_dependent=True)
    many2one_id = fields.Many2one(comodel_name="test_read_group.order")
    name = fields.Char()
    fold = fields.Boolean()

    @property
    def _order(self):
        if self.env.context.get("test_read_group_order_company_dependent"):
            return "company_dependent_name"
        return super()._order


class Test_Read_GroupOrderLine(models.Model):
    _name = "test_read_group.order.line"
    _description = "Sales order line"

    order_id = fields.Many2one(comodel_name="test_read_group.order")
    order_expand_id = fields.Many2one(
        comodel_name="test_read_group.order",
        group_expand="_read_group_expand_full",
    )
    value = fields.Integer()
    date = fields.Date(related="order_id.date")
    current_order_id = fields.Many2one(
        comodel_name="test_read_group.order",
        compute="_compute_current_order_id",
        group_by_field="order_id",
    )

    @api.depends("order_id")
    def _compute_current_order_id(self):
        for line in self:
            line.current_order_id = line.order_id


class Test_Read_GroupUser(models.Model):
    _name = "test_read_group.user"
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        comodel_name="test_read_group.task",
        relation="test_read_group_task_user_rel",
        column1="user_id",
        column2="task_id",
        string="Tasks",
    )


class Test_Read_GroupTask(models.Model):
    _name = "test_read_group.task"
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        comodel_name="test_read_group.user",
        relation="test_read_group_task_user_rel",
        column1="task_id",
        column2="user_id",
        string="Collaborators",
    )
    customer_ids = fields.Many2many(
        comodel_name="test_read_group.user",
        relation="test_read_group_task_user_rel_2",
        column1="task_id",
        column2="user_id",
        string="Customers",
    )
    tag_ids = fields.Many2many(
        comodel_name="test_read_group.tag",
        relation="test_read_group_task_tag_rel",
        column1="task_id",
        column2="tag_id",
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        comodel_name="test_read_group.tag",
        relation="test_read_group_task_tag_rel",
        column1="task_id",
        column2="tag_id",
        string="Active Tags",
        domain=[("active", "=", True)],
    )
    all_tag_ids = fields.Many2many(
        comodel_name="test_read_group.tag",
        relation="test_read_group_task_tag_rel",
        column1="task_id",
        column2="tag_id",
        string="All Tags",
        context={"active_test": False},
    )
    date = fields.Date()
    integer = fields.Integer()
    key = fields.Char()
    lead_user_id = fields.Many2one(
        comodel_name="test_read_group.user",
        compute="_compute_lead_user_id",
        group_by_field="user_ids",
    )
    ref = fields.Char(order_by_field="id")
    parity = fields.Selection(
        [("odd", "Odd"), ("even", "Even")],
        compute="_compute_parity",
        group_by_sql="_parity_group_sql",
        order_by_sql="_parity_order_sql",
    )
    integer_squared = fields.Integer(
        compute="_compute_integer_squared", value_sql="_integer_squared_sql"
    )
    integer_doubled = fields.Integer(compute="_compute_integer_doubled")
    is_big = fields.Boolean(compute="_compute_integer_doubled")

    @api.depends("user_ids")
    def _compute_lead_user_id(self):
        for task in self:
            task.lead_user_id = task.user_ids[:1]

    @api.depends("integer")
    def _compute_parity(self):
        for task in self:
            task.parity = "even" if task.integer % 2 == 0 else "odd"

    @api.depends("integer")
    def _compute_integer_doubled(self):
        for task in self:
            task.integer_doubled = task.integer * 2
            task.is_big = task.integer >= 4

    @api.depends("integer")
    def _compute_integer_squared(self):
        for task in self:
            task.integer_squared = task.integer * task.integer

    def _integer_squared_sql(self, field, alias, query):
        integer = self._field_to_sql(alias, "integer", query)
        return SQL("(%s * %s)", integer, integer)

    def _parity_sql(self, alias, query):
        return SQL(
            "CASE WHEN %s %% 2 = 0 THEN 'even' ELSE 'odd' END",
            self._field_to_sql(alias, "integer", query),
        )

    def _parity_group_sql(self, field, alias, query):
        return self._parity_sql(alias, query)

    def _parity_order_sql(self, field, alias, direction, nulls, query):
        return self._order_value_to_sql(
            self._parity_sql(alias, query), direction, nulls, query
        )


class Test_Read_GroupTag(models.Model):
    _name = "test_read_group.tag"
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class Test_Read_GroupPrefixCollision(models.Model):
    _name = "test_read_group.prefix_collision"
    _description = "Prefix-colliding groupby specs (tag / tag_id)"

    tag = fields.Many2many(
        comodel_name="test_read_group.tag",
        relation="trg_prefix_tag_rel",
        string="Tag (m2m)",
    )
    tag_id = fields.Many2one(
        comodel_name="test_read_group.tag",
        string="Tag (m2o)",
    )
    value = fields.Integer()


class ResPartner(models.Model):
    _inherit = "res.partner"

    date = fields.Date()


class Test_Read_GroupRelated_Bar(models.Model):
    _name = "test_read_group.related_bar"
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many(
        comodel_name="test_read_group.related_foo",
        inverse_name="bar_id",
    )
    foo_names_sudo = fields.Char(
        related="foo_ids.name",
        string="name_one2many_related",
    )

    base_ids = fields.Many2many(comodel_name="test_read_group.related_base")
    computed_base_ids = fields.Many2many(
        comodel_name="test_read_group.related_base",
        compute="_compute_computed_base_ids",
    )

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class Test_Read_GroupRelated_Foo(models.Model):
    _name = "test_read_group.related_foo"
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one(comodel_name="test_read_group.related_bar")

    bar_name_sudo = fields.Char(
        related="bar_id.name",
        string="bar_name_sudo",
    )
    bar_name = fields.Char(
        related="bar_id.name",
        string="bar_name",
        related_sudo=False,
    )

    bar_base_ids = fields.Many2many(related="bar_id.base_ids")

    schedule_datetime = fields.Datetime()


class Test_Read_GroupRelated_Base(models.Model):
    _name = "test_read_group.related_base"
    _description = "RelatedBase"

    name = fields.Char()
    value = fields.Integer()
    foo_id = fields.Many2one(comodel_name="test_read_group.related_foo")

    foo_id_name = fields.Char(
        related="foo_id.name",
        string="foo_id_name",
        related_sudo=False,
    )
    foo_id_name_sudo = fields.Char(
        related="foo_id.name",
        string="foo_id_name_sudo",
    )

    foo_id_bar_id_name = fields.Char(
        related="foo_id.bar_id.name",
        string="foo_bar_name_sudo",
    )
    foo_id_bar_name = fields.Char(
        related="foo_id.bar_name",
        string="foo_bar_name_sudo_1",
    )
    foo_id_bar_name_sudo = fields.Char(
        related="foo_id.bar_name_sudo",
        string="foo_bar_name_sudo_2",
    )


class Test_Read_GroupRelated_Inherits(models.Model):
    _name = "test_read_group.related_inherits"
    _description = "RelatedInherits"
    _inherits = {
        "test_read_group.related_base": "base_id",
    }

    base_id = fields.Many2one(
        comodel_name="test_read_group.related_base",
        required=True,
        ondelete="cascade",
    )


class Test_Read_GroupChain_Inherits(models.Model):
    _name = "test_read_group.chain_inherits"
    _description = "ChainInherits"

    inherited_id = fields.Many2one(
        comodel_name="test_read_group.related_inherits",
        required=True,
    )
