"""RAG validation flag — one row per warning from the validation step.

When the ``ValidationVerdict.flags`` list contains entries like
``'unusual_amount'``, ``'no_history'``, or ``'low_account_confidence'``,
one ``invoice.agent.validation.flag`` row is created on the ``account.move``
so the accountant sees the specific warnings on the form.

Flags are informational — they never block posting or change routing.
They are cleared and re-created each time a validation runs, so the
flag list always reflects the latest verdict.
"""

from odoo import fields, models


class InvoiceAgentValidationFlag(models.Model):
    _name = "invoice.agent.validation.flag"
    _description = "AI validation flag (RAG verdict)"
    _rec_name = "flag"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    flag = fields.Char(
        string="Flag Code",
        required=True,
        readonly=True,
        help="Short code from the ValidationVerdict.flags list: "
        "'unusual_amount', 'no_history', 'low_account_confidence'.",
    )
    reasoning = fields.Text(
        string="Reasoning",
        readonly=True,
        help="Detailed explanation from the validation step for why "
        "this flag was raised.",
    )
