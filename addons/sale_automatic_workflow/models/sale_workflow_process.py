# Copyright 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>
# Copyright 2013 Camptocamp SA (author: Guewen Baconnier)
# Copyright 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleWorkflowProcess(models.Model):
    """A workflow process is the setup of the automation of a sales order.

    Each sales order can be linked to a workflow process.
    Then, the options of the workflow will change how the sales order
    behave, and how it is automatized.

    A workflow process may be linked with a Sales payment method, so
    each time a payment method is used, the workflow will be applied.
    """

    _name = "sale.workflow.process"
    _description = "Sale Workflow Process"

    @api.model
    def _default_filter(self, xmlid):
        record = self.env.ref(xmlid, raise_if_not_found=False)
        if record:
            return record
        return self.env["ir.filters"].browse()

    name = fields.Char(required=True)
    picking_policy = fields.Selection(
        selection=[
            ("direct", "Deliver each product when available"),
            ("one", "Deliver all products at once"),
        ],
        string="Shipping Policy",
        default="direct",
    )
    validate_order = fields.Boolean()
    send_order_confirmation_mail = fields.Boolean(
        help="When checked, after order confirmation, a confirmation email will be "
        "sent (if not already sent).",
    )
    order_filter_domain = fields.Text(
        string="Order Filter Domain", related="order_filter_id.domain"
    )
    create_invoice = fields.Boolean()
    create_invoice_filter_domain = fields.Text(
        string="Create Invoice Filter Domain", related="create_invoice_filter_id.domain"
    )
    validate_invoice = fields.Boolean()
    validate_invoice_filter_domain = fields.Text(
        string="Validate Invoice Filter Domain",
        related="validate_invoice_filter_id.domain",
    )
    send_invoice = fields.Boolean()
    send_invoice_filter_domain = fields.Text(
        string="Send Invoice Filter Domain",
        related="send_invoice_filter_id.domain",
    )
    validate_picking = fields.Boolean(string="Confirm and Transfer Picking")
    picking_filter_domain = fields.Text(
        string="Picking Filter Domain", related="picking_filter_id.domain"
    )
    invoice_date_is_order_date = fields.Boolean(
        string="Force Invoice Date",
        help="When checked, the invoice date will be " "the same than the order's date",
    )

    invoice_service_delivery = fields.Boolean(
        string="Invoice Service on delivery",
        help="If this box is checked, when the first invoice is created "
        "The service sale order lines will be included and will be "
        "marked as delivered",
    )
    sale_done = fields.Boolean()
    sale_done_filter_domain = fields.Text(
        string="Sale Done Filter Domain", related="sale_done_filter_id.domain"
    )
    warning = fields.Text(
        "Warning Message",
        translate=True,
        help="If set, displays the message when an user"
        "selects the process on a sale order",
    )
    team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team")
    property_journal_id = fields.Many2one(
        comodel_name="account.journal",
        company_dependent=True,
        string="Sales Journal",
        help="Set default journal to use on invoice",
    )
    order_filter_id = fields.Many2one(
        "ir.filters",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow.automatic_workflow_order_filter"
        ),
    )
    picking_filter_id = fields.Many2one(
        "ir.filters",
        string="Picking Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow.automatic_workflow_picking_filter"
        ),
    )
    create_invoice_filter_id = fields.Many2one(
        "ir.filters",
        string="Create Invoice Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow.automatic_workflow_create_invoice_filter"
        ),
    )
    validate_invoice_filter_id = fields.Many2one(
        "ir.filters",
        string="Validate Invoice Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow." "automatic_workflow_validate_invoice_filter"
        ),
    )
    send_invoice_filter_id = fields.Many2one(
        "ir.filters",
        string="Send Invoice Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow." "automatic_workflow_send_invoice_filter"
        ),
    )
    sale_done_filter_id = fields.Many2one(
        "ir.filters",
        string="Sale Done Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow.automatic_workflow_sale_done_filter"
        ),
    )
    payment_filter_id = fields.Many2one(
        comodel_name="ir.filters",
        string="Register Payment Invoice Filter",
        default=lambda self: self._default_filter(
            "sale_automatic_workflow.automatic_workflow_payment_filter"
        ),
    )
    register_payment = fields.Boolean()
    payment_filter_domain = fields.Text(
        related="payment_filter_id.domain",
    )
