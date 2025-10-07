# Copyright 2018-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CommissionMixin(models.AbstractModel):
    _name = "commission.mixin"
    _description = (
        "Mixin model for applying to any object that wants to handle commissions"
    )

    agent_ids = fields.One2many(
        comodel_name="commission.line.mixin",
        inverse_name="object_id",
        string="Agents & commissions",
        help="Agents/Commissions related to the invoice line.",
        compute="_compute_agent_ids",
        readonly=False,
        store=True,
        copy=True,
    )
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    commission_free = fields.Boolean(
        string="Comm. free",
        compute="_compute_commission_free",
        store=True,
        readonly=True,
    )
    commission_status = fields.Char(
        compute="_compute_commission_status",
        string="Commission",
    )

    def _prepare_agent_vals(self, agent):
        return {"agent_id": agent.id, "commission_id": agent.commission_id.id}

    def _prepare_agents_vals_partner(self, partner, settlement_type=None):
        """Utility method for getting agents creation dictionary of a partner."""
        agents = partner.agent_ids
        if settlement_type:
            agents = agents.filtered(
                lambda x: not x.commission_id.settlement_type
                or x.commission_id.settlement_type == settlement_type
            )
        return [(0, 0, self._prepare_agent_vals(agent)) for agent in agents]

    @api.depends("commission_free")
    def _compute_agent_ids(self):
        """Empty method that needs to be implemented in children models."""
        raise NotImplementedError()

    @api.depends("product_id")
    def _compute_commission_free(self):
        """Compute instead of a simple related to have a proper initialized value."""
        for line in self:
            line.commission_free = line.product_id.commission_free

    @api.depends("commission_free", "agent_ids")
    def _compute_commission_status(self):
        for line in self:
            if line.commission_free:
                line.commission_status = _("Comm. free")
            elif len(line.agent_ids) == 0:
                line.commission_status = _("No commission agents")
            elif len(line.agent_ids) == 1:
                line.commission_status = _("1 commission agent")
            else:
                line.commission_status = _("%s commission agents") % (
                    len(line.agent_ids),
                )

    def recompute_agents(self):
        self._compute_agent_ids()

    def button_edit_agents(self):
        self.ensure_one()
        view = self.env.ref("commission.view_commission_mixin_agent_only")
        return {
            "name": _("Agents"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self._name,
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
            "context": self.env.context,
        }


class CommissionLineMixin(models.AbstractModel):
    _name = "commission.line.mixin"
    _description = (
        "Mixin model for having commission agent lines in "
        "any object inheriting from this one"
    )
    _rec_name = "agent_id"

    _sql_constraints = [
        (
            "unique_agent",
            "UNIQUE(object_id, agent_id)",
            "You can only add one time each agent.",
        )
    ]

    object_id = fields.Many2one(
        comodel_name="commission.mixin",
        ondelete="cascade",
        required=True,
        copy=False,
        string="Parent",
    )
    agent_id = fields.Many2one(
        comodel_name="res.partner",
        domain="[('agent', '=', True)]",
        ondelete="restrict",
        required=True,
    )
    commission_id = fields.Many2one(
        comodel_name="commission",
        ondelete="restrict",
        required=True,
        compute="_compute_commission_id",
        store=True,
        readonly=False,
        copy=True,
    )
    amount = fields.Monetary(
        string="Commission Amount",
        compute="_compute_amount",
        store=True,
    )
    # Fields to be overriden with proper source (via related or computed field)
    currency_id = fields.Many2one(comodel_name="res.currency")

    def _compute_amount(self):
        """Compute method to be implemented by inherited models."""
        raise NotImplementedError()

    def _get_commission_amount(self, commission, subtotal, product, quantity):
        """Get the commission amount for the data given. It's called by
        compute methods of children models.

        This means the inheritable method for modifying the amount of the commission.
        """
        self.ensure_one()
        if product.commission_free or not commission:
            return 0.0
        if commission.amount_base_type == "net_amount":
            # If subtotal (sale_price * quantity) is less than
            # standard_price * quantity, it means that we are selling at
            # lower price than we bought, so set amount_base to 0
            subtotal = max([0, subtotal - product.standard_price * quantity])
        if commission.commission_type == "fixed":
            return subtotal * (commission.fix_qty / 100.0)
        elif commission.commission_type == "section":
            return commission.calculate_section(subtotal)

    @api.depends("agent_id")
    def _compute_commission_id(self):
        for record in self:
            record.commission_id = record.agent_id.commission_id
