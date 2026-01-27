from odoo import api, fields, models, _


class KitchenTicket(models.Model):
    _name = "restaurant.kitchen_ticket"
    _description = "Kitchen Ticket"
    _order = "create_date desc"

    name = fields.Char(
        string="Ticket No.",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    table_id = fields.Many2one(
        "pos.restaurant.table",
        string="Table",
        required=False,
        help="Table related to this ticket.",
    )
    state = fields.Selection(
        [
            ("new", "新規"),
            ("in_progress", "調理中"),
            ("done", "提供済"),
        ],
        string="Status",
        default="new",
        tracking=True,
    )
    line_ids = fields.One2many(
        "restaurant.kitchen_ticket_line",
        "ticket_id",
        string="Lines",
    )
    note = fields.Text(string="全体メモ")

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New"):
            seq = self.env["ir.sequence"].next_by_code("restaurant.kitchen_ticket") or _("New")
            vals["name"] = seq
        return super().create(vals)


class KitchenTicketLine(models.Model):
    _name = "restaurant.kitchen_ticket_line"
    _description = "Kitchen Ticket Line"

    ticket_id = fields.Many2one(
        "restaurant.kitchen_ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="メニュー",
        required=True,
    )
    qty = fields.Float(
        string="数量",
        default=1.0,
    )
    note = fields.Char(
        string="備考",
        help="辛さ、トッピング、抜き指定などのメモ。",
    )
    area = fields.Selection(
        [
            ("kitchen", "キッチン"),
            ("drink", "ドリンク"),
            ("dessert", "デザート"),
        ],
        string="担当エリア",
        default="kitchen",
    )
