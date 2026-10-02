# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class CommissionSettlement(models.Model):
    _name = "commission.settlement"
    _description = "Settlement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    total = fields.Float(compute="_compute_total", readonly=True, store=True)
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    agent_id = fields.Many2one(
        comodel_name="res.partner",
        domain="[('agent', '=', True)]",
        required=True,
    )
    agent_type = fields.Selection(related="agent_id.agent_type")
    settlement_type = fields.Selection(
        selection=[("manual", "Manual")],
        default="manual",
        readonly=True,
        required=True,
        help="The source of the settlement, e.g. 'Sales invoice', 'Sales order', "
        "'Purchase order'...",
    )
    can_edit = fields.Boolean(
        compute="_compute_can_edit",
        help="Technical field for determining if user can edit settlements",
        store=True,
    )
    line_ids = fields.One2many(
        comodel_name="commission.settlement.line",
        inverse_name="settlement_id",
        string="Settlement lines",
    )
    state = fields.Selection(
        selection=[
            ("settled", "Settled"),
            ("cancel", "Canceled"),
        ],
        readonly=True,
        required=True,
        default="settled",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
        default=lambda self: self._default_currency_id(),
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self._default_company_id(),
        required=True,
    )

    def _default_currency_id(self):
        return self.env.company.currency_id.id

    def _default_company_id(self):
        return self.env.company.id

    @api.depends("line_ids", "line_ids.settled_amount")
    def _compute_total(self):
        for record in self:
            record.total = sum(record.mapped("line_ids.settled_amount"))

    @api.depends("settlement_type")
    def _compute_can_edit(self):
        for record in self:
            record.can_edit = record.settlement_type == "manual"

    def action_cancel(self):
        self.write({"state": "cancel"})

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get("agent_id"):
            res.append((updated_values["agent_id"], subtype_ids, False))
        return res


class SettlementLine(models.Model):
    _name = "commission.settlement.line"
    _description = "Line of a commission settlement"

    settlement_id = fields.Many2one(
        "commission.settlement",
        readonly=True,
        ondelete="cascade",
        required=True,
    )
    date = fields.Date(
        compute="_compute_date",
        readonly=False,
        store=True,
        required=True,
    )
    agent_id = fields.Many2one(
        comodel_name="res.partner",
        related="settlement_id.agent_id",
        store=True,
    )
    settled_amount = fields.Monetary(
        compute="_compute_settled_amount", readonly=False, store=True
    )
    currency_id = fields.Many2one(
        related="settlement_id.currency_id",
        comodel_name="res.currency",
        store=True,
        readonly=True,
    )
    commission_id = fields.Many2one(
        comodel_name="commission",
        compute="_compute_commission_id",
        readonly=False,
        store=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="settlement_id.company_id",
        store=True,
    )

    def _compute_date(self):
        """Empty hook for allowing in children modules to auto-compute this field
        depending on the settlement line source.
        """

    def _compute_commission_id(self):
        """Empty hook for allowing in children modules to auto-compute this field
        depending on the settlement line source.
        """

    def _compute_settled_amount(self):
        """Empty container for allowing in children modules to auto-compute this
        amount depending on the settlement line source.
        """
