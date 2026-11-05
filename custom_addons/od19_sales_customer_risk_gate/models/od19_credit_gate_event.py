from odoo import fields, models


class Od19CreditGateEvent(models.Model):
    _name = "od19.credit.gate.event"
    _description = "OD19 Credit Gate Blocked Event"
    _order = "create_date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
        index=True,
    )
    reason_code = fields.Selection(
        selection=[
            ("blacklist", "Blacklist"),
            ("credit", "Credit"),
            ("credit_hold", "Credit Aging Hold"),
        ],
        string="Reason",
        required=True,
        index=True,
    )
    stage = fields.Selection(
        selection=[
            ("quotation_create", "Quotation Create"),
            ("quotation_write", "Quotation Write"),
            ("order_confirm", "Order Confirm"),
            ("rfq_create", "RFQ Create"),
            ("rfq_write", "RFQ Write"),
            ("purchase_confirm", "Purchase Confirm"),
            ("credit_revalidation", "Credit Revalidation"),
        ],
        string="Stage",
        required=True,
        index=True,
    )
    order_ref = fields.Char(string="Document Reference", readonly=True)
