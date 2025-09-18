from odoo import api, fields, models


class Test_PerformanceBase(models.Model):
    _name = "test_performance.base"
    _description = "Test Performance Base"

    name = fields.Char()
    value = fields.Integer(default=0)
    value_pc = fields.Float(compute="_value_pc", store=True)
    value_ctx = fields.Float(compute="_value_ctx")
    computed_value = fields.Float(compute="_computed_value")
    indirect_computed_value = fields.Float(compute="_indirect_computed_value")
    partner_id = fields.Many2one("res.partner", string="Customer")

    line_ids = fields.One2many("test_performance.line", "base_id")
    total = fields.Integer(compute="_total", store=True)
    tag_ids = fields.Many2many("test_performance.tag")

    @api.depends("value")
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100

    @api.depends("value")
    def _computed_value(self):
        for record in self:
            record.computed_value = float(record.value) / 100

    @api.depends("computed_value")
    def _indirect_computed_value(self):
        for record in self:
            record.indirect_computed_value = record.computed_value / 100

    @api.depends_context("key")
    def _value_ctx(self):
        self.env.cr.execute("SELECT 42")  # one dummy query per batch
        for record in self:
            record.value_ctx = self.env.context.get("key")

    @api.depends("line_ids.value")
    def _total(self):
        for record in self:
            record.total = sum(line.value for line in record.line_ids)


class Test_PerformanceLine(models.Model):
    _name = "test_performance.line"
    _description = "Test Performance Line"

    base_id = fields.Many2one(
        "test_performance.base", required=True, ondelete="cascade"
    )
    value = fields.Integer()

    _line_uniq = models.UniqueIndex(
        "(base_id, value)", "base_id and value should be unique"
    )


class Test_PerformanceTag(models.Model):
    _name = "test_performance.tag"
    _description = "Test Performance Tag"

    name = fields.Char()


class Test_PerformanceBacon(models.Model):
    _name = "test_performance.bacon"
    _description = "Test Performance Bacon"

    property_eggs = fields.Many2one(
        "test_performance.eggs", company_dependent=True, string="Eggs"
    )


class Test_PerformanceEggs(models.Model):
    _name = "test_performance.eggs"
    _description = "Test Performance Eggs"

    name = fields.Char()


class Test_PerformanceMozzarella(models.Model):
    _name = "test_performance.mozzarella"
    _description = "Test Performance Mozzarella"

    value = fields.Integer(default=0, required=True)
    value_plus_one = fields.Integer(
        compute="_value_plus_one", required=True, store=True
    )
    value_null_by_default = fields.Integer()

    @api.depends("value")
    def _value_plus_one(self):
        for record in self:
            record.value_plus_one = record.value + 1


class Test_PerformanceSimpleMinded(models.Model):
    _name = "test_performance.simple.minded"
    _description = "test_performance.simple.minded"

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one("test_performance.simple.minded")

    child_ids = fields.One2many("test_performance.simple.minded", "parent_id")


class Test_PerformanceAllTypes(models.Model):
    """Model with every field type for field conversion benchmarks."""

    _name = "test_performance.all_types"
    _description = "Test Performance All Field Types"

    name = fields.Char(default="bench")
    active = fields.Boolean(default=True)
    f_integer = fields.Integer(default=42)
    f_float = fields.Float(default=3.14, digits=(10, 4))
    f_monetary = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    f_char = fields.Char(default="hello world")
    f_text = fields.Text(default="A longer text value for benchmarking purposes.")
    f_boolean = fields.Boolean(default=True)
    f_date = fields.Date(default="2025-06-15")
    f_datetime = fields.Datetime(default="2025-06-15 10:30:00")
    f_selection = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("close", "Closed"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )
    f_binary = fields.Binary()
    f_json = fields.Json()
    f_many2one = fields.Many2one("res.partner")
    f_one2many = fields.One2many("test_performance.all_types.line", "parent_id")
    f_many2many = fields.Many2many("test_performance.tag")
    f_html = fields.Html()

    f_computed = fields.Float(compute="_compute_f_computed", store=True)

    @api.depends("f_integer", "f_float")
    def _compute_f_computed(self):
        for rec in self:
            rec.f_computed = rec.f_integer * rec.f_float


class Test_PerformanceAllTypesLine(models.Model):
    _name = "test_performance.all_types.line"
    _description = "Test Performance All Types Line"

    parent_id = fields.Many2one(
        "test_performance.all_types", required=True, ondelete="cascade"
    )
    value = fields.Integer()
