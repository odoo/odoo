from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EventBooth(models.Model):
    _inherit = "event.booth"

    # registrations
    event_booth_registration_ids = fields.One2many(
        comodel_name="event.booth.registration",
        inverse_name="event_booth_id",
    )
    # sale information
    sale_order_line_registration_ids = fields.Many2many(
        comodel_name="sale.order.line",
        relation="event_booth_registration",
        column1="event_booth_id",
        column2="sale_order_line_id",
        string="SO Lines with reservations",
        copy=False,
        groups="sale.group_sale_salesman",
    )
    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Final Sale Order Line",
        index="btree_not_null",
        copy=False,
        readonly=False,
        ondelete="set null",
        groups="sale.group_sale_salesman",
    )
    sale_order_id = fields.Many2one(  # noqa: E8529  One2many inverse of sale.order.event_booth_ids
        related="sale_order_line_id.order_id",
        store=True,
        index="btree_not_null",
        readonly=True,
        groups="sale.group_sale_salesman",
    )
    is_paid = fields.Boolean(copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_sale_order(self):
        booth_with_so = self.sudo().filtered("sale_order_id")
        if booth_with_so:
            raise UserError(
                _(
                    "You can't delete the following booths as they are linked to sales orders: "
                    "%(booths)s",
                    booths=", ".join(booth_with_so.mapped("name")),
                )
            )

    def action_set_paid(self):
        self.write({"is_paid": True})

    def action_view_sale_order(self):
        self.sale_order_id.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale.action_sale_order"
        )
        action["views"] = [(False, "form")]
        action["res_id"] = self.sale_order_id.id
        return action

    def _get_booth_multiline_description(self):
        return "%s : \n%s" % (
            self.event_id.display_name,
            "\n".join(["- %s" % booth.name for booth in self]),
        )
