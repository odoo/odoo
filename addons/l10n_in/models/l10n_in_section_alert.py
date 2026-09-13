from odoo import _, api, fields, models


class L10n_InSectionAlert(models.Model):
    _name = "l10n_in.section.alert"
    _description = "indian section alert"

    name = fields.Char(string="Section Name")
    tax_source_type = fields.Selection(
        selection=[
            ("tds", "TDS"),
            ("tcs", "TCS"),
        ]
    )
    consider_amount = fields.Selection(
        selection=[
            ("untaxed_amount", "Untaxed Amount"),
            ("total_amount", "Total Amount"),
        ],
        string="Consider",
        default="untaxed_amount",
        required=True,
    )
    is_per_transaction_limit = fields.Boolean(string="Per Transaction")
    per_transaction_limit = fields.Float(string="Per Transaction limit")
    is_aggregate_limit = fields.Boolean(string="Aggregate")
    aggregate_limit = fields.Float(string="Aggregate limit")
    aggregate_period = fields.Selection(
        selection=[
            ("monthly", "Monthly"),
            ("fiscal_yearly", "Financial Yearly"),
        ],
        default="fiscal_yearly",
    )
    l10n_in_section_tax_ids = fields.One2many(
        comodel_name="account.tax",
        inverse_name="l10n_in_section_id",
        string="Taxes",
    )
    tax_report_line_id = fields.Many2one(comodel_name="account.report.line")

    _per_transaction_limit = models.Constraint(
        "CHECK(per_transaction_limit >= 0)",
        "Per transaction limit must be positive",
    )
    _aggregate_limit = models.Constraint(
        "CHECK(aggregate_limit >= 0)",
        "Aggregate limit must be positive",
    )

    @api.depends("tax_source_type")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.tax_source_type.upper()} {record.name or ''}"
                if record.tax_source_type
                else f"{record.name or ''}"
            )

    def _get_warning_message(self):
        warning = ", ".join(self.mapped("name"))
        section_type = next(iter(set(self.mapped("tax_source_type")))).upper()
        action = _("collect") if section_type == "TCS" else _("deduct")
        return _(
            "It's advisable to %(action)s %(section_type)s u/s %(warning)s on this transaction.",
            action=action,
            section_type=section_type,
            warning=warning,
        )
