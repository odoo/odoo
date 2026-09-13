from odoo import api, fields, models


class PerfCmpRel(models.Model):
    _name = "perf.cmp.rel"
    _description = "Perf Compare Related (many2one target)"

    name = fields.Char()


class PerfCmpTag(models.Model):
    _name = "perf.cmp.tag"
    _description = "Perf Compare Tag (many2many target)"

    name = fields.Char()


class PerfCmpBase(models.Model):
    _name = "perf.cmp.base"
    _description = "Perf Compare Base"

    name = fields.Char()
    value = fields.Integer(default=0)
    amount = fields.Float()
    flag = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )
    a_date = fields.Date()
    a_datetime = fields.Datetime()

    rel_id = fields.Many2one(comodel_name="perf.cmp.rel")
    line_ids = fields.One2many(
        comodel_name="perf.cmp.line",
        inverse_name="base_id",
    )
    tag_ids = fields.Many2many(comodel_name="perf.cmp.tag")

    value_pc = fields.Float(
        compute="_compute_value_pc",
        store=True,
    )
    total = fields.Integer(
        compute="_compute_total",
        store=True,
    )

    @api.depends("value")
    def _compute_value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100

    @api.depends("line_ids.value")
    def _compute_total(self):
        for record in self:
            record.total = sum(line.value for line in record.line_ids)


class PerfCmpLine(models.Model):
    _name = "perf.cmp.line"
    _description = "Perf Compare Line"

    base_id = fields.Many2one(
        comodel_name="perf.cmp.base",
        required=True,
        ondelete="cascade",
    )
    value = fields.Integer()
