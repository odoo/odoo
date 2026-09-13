import uuid

from odoo import _, fields, models

CHECK_TYPES = [
    ("check", "Check"),
    ("file", "Upload Document"),
]


class AccountReturnCheckTemplate(models.Model):
    _name = "account.return.check.template"
    _description = "Account Return Check Template"

    name = fields.Char(
        string="Title",
        translate=True,
        required=True,
    )
    code = fields.Char(
        default=lambda r: f"_template_check_{uuid.uuid4()}",
        copy=False,
    )
    return_type = fields.Many2one(
        comodel_name="account.return.type",
        string="Tax Return/Audit",
        required=True,
    )
    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Applicable Countries",
    )
    cycle = fields.Selection(
        selection=[
            ("regulatory_compliance", "Regulatory compliance"),
            ("treasury_financing", "Treasury and financing"),
            ("purchases", "Purchases"),
            ("operating_expenses", "Operating expenses"),
            ("sales", "Sales"),
            ("inventory", "Inventory"),
            ("fixed_assets", "Fixed assets"),
            ("payroll", "Payroll"),
            ("state", "Government"),
            ("equity", "Equity"),
            ("other", "Others"),
        ],
        default="other",
        required=True,
    )
    type = fields.Selection(
        selection=CHECK_TYPES,
        default="check",
        required=True,
    )

    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        string="Action on Click",
        help="Overrides the default action based on the model and domain.",
    )
    additional_action_domain = fields.Char()
    additional_action_context = fields.Char()
    additional_action_params = fields.Char()
    activity_type = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activities",
    )

    description = fields.Text(translate=True)
    model = fields.Selection(
        selection=[
            ("account.move.line", "Journal Item"),
            ("account.move", "Journal Entry"),
            ("account.bank.statement.line", "Bank Statement Line"),
            ("account.payment", "Payments"),
        ]
    )
    domain = fields.Char()

    def _get_default_check_action_from_model(self):
        if self.model == "account.bank.statement.line":
            return {
                "type": "ir.actions.act_window",
                "name": _("Bank Matching"),
                "res_model": "account.bank.statement.line",
                "view_mode": "kanban,list",
                "search_view_id": self.env.ref(
                    "account.view_bank_statement_line_search_bank_rec_widget"
                ).id,
                "views": [
                    [
                        self.env.ref(
                            "account.view_bank_statement_line_kanban_bank_rec_widget"
                        ).id,
                        "kanban",
                    ],
                    [False, "list"],
                ],
                "domain": [("state", "!=", "cancel")],
            }

        return False
