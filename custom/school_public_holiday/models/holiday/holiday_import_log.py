from odoo import _, api, fields, models


class SchoolHolidayImportLog(models.Model):
    _name = "school.holiday.import.log"
    _description = "Holiday History Log"
    _order = "import_date desc, id desc"

    name = fields.Char(string="File Name", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="Imported By",
        default=lambda self: self.env.user,
        required=True,
    )
    import_date = fields.Datetime(
        string="Import Date",
        default=fields.Datetime.now,
        required=True,
    )
    duplicate_policy = fields.Selection(
        [
            ("skip", "Skip Existing"),
            ("update", "Update Existing"),
        ],
        string="Duplicate Policy",
        default="skip",
    )
    total_records = fields.Integer(string="Total Rows", default=0)
    records_created = fields.Integer(string="Created", default=0)
    records_updated = fields.Integer(string="Updated", default=0)
    records_skipped = fields.Integer(string="Skipped", default=0)
    records_failed = fields.Integer(string="Failed", default=0)
    error_log = fields.Text(string="Errors & Warnings")
    holiday_ids = fields.One2many(
        "university.holiday",
        "import_batch_id",
        string="Imported Holidays",
    )
    holiday_count = fields.Integer(
        string="Holidays Count",
        compute="_compute_holiday_count",
    )

    @api.depends("holiday_ids")
    def _compute_holiday_count(self):
        for log in self:
            log.holiday_count = len(log.holiday_ids)

    def action_view_holidays(self):
        self.ensure_one()
        return {
            "name": _("Holidays Imported from %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.holiday",
            "view_mode": "list,form",
            "domain": [("import_batch_id", "=", self.id)],
            "context": {"default_import_batch_id": self.id},
        }
