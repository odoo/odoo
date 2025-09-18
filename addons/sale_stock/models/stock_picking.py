from odoo import api, Command, fields, models
from odoo.tools.sql import column_exists, create_column


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        compute="_compute_sale_id",
        store=True,
        inverse="_set_sale_id",
        index="btree_not_null",
    )
    delay_pass = fields.Datetime(
        compute="_compute_date_order",
        search="_search_delay_pass",
        copy=False,
        index=True,
    )
    days_to_deliver = fields.Datetime(
        compute="_compute_date_effective",
        search="_search_days_to_deliver",
        copy=False,
    )

    # ------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------

    def _auto_init(self):
        """
        Create related field here, too slow
        when computing it afterwards through _compute_related.

        Since group_id.sale_id is created in this module,
        no need for an UPDATE statement.
        """
        if not column_exists(self.env.cr, "stock_picking", "sale_id"):
            create_column(self.env.cr, "stock_picking", "sale_id", "int4")
        return super()._auto_init()

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("reference_ids.sale_ids", "move_ids.sale_line_id.order_id")
    def _compute_sale_id(self):
        for picking in self:
            # picking and move should have a link to the SO to see the picking on the stat button.
            # This will filter the move chain to the delivery moves only.
            # First try from moves, then fall back to reference_ids for untracked deliveries.
            picking.sale_id = (
                picking.move_ids.sale_line_id.order_id
                or picking.reference_ids.sale_ids[:1]
            )

    @api.depends("move_ids.sale_line_id")
    def _compute_move_type(self):
        super()._compute_move_type()
        for picking in self:
            sale_orders = picking.move_ids.sale_line_id.order_id
            if sale_orders:
                if any(so.picking_policy == "direct" for so in sale_orders):
                    picking.move_type = "direct"
                else:
                    picking.move_type = "one"

    def _compute_date_order(self):
        for picking in self:
            picking.delay_pass = (
                picking.sale_id.date_order
                if picking.sale_id
                else fields.Datetime.now()
            )

    @api.depends("state", "location_dest_id.usage", "date_done")
    def _compute_date_effective(self):
        for picking in self:
            if (
                picking.state == "done"
                and picking.location_dest_id.usage == "customer"
                and picking.date_done
            ):
                picking.days_to_deliver = picking.date_done
            else:
                picking.days_to_deliver = False

    # ------------------------------------------------------------
    # INVERSE METHODS
    # ------------------------------------------------------------

    def _set_sale_id(self):
        if self.reference_ids:
            if self.sale_id:
                self.reference_ids.sale_ids = [Command.link(self.sale_id.id)]
            else:
                sale_order = self.move_ids.sale_line_id.order_id
                if len(sale_order) == 1:
                    self.reference_ids.sale_ids = [Command.unlink(sale_order.id)]
        else:
            if self.sale_id:
                reference = self.env["stock.reference"].create(
                    {
                        "sale_ids": [Command.link(self.sale_id.id)],
                        "name": self.sale_id.name,
                    },
                )
                self._add_reference(reference)
        self.move_ids._reassign_sale_lines(self.sale_id)

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    @api.model
    def _search_days_to_deliver(self, operator, value):
        return [("date_done", operator, value)]

    @api.model
    def _search_delay_pass(self, operator, value):
        return [("sale_id.date_order", operator, value)]

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _log_less_quantities_than_expected(self, moves):
        """Log an activity on sale order that are linked to moves. The
        note summarize the real processed quantity and promote a
        manual action.

        :param dict moves: a dict with a move as key and tuple with
        new and old quantity as value. eg: {move_1 : (4, 5)}
        """

        def _keys_in_groupby(sale_line):
            """group by order_id and the sale_person on the order"""
            return (sale_line.order_id, sale_line.order_id.user_id)

        def _render_note_exception_quantity(moves_information):
            """Generate a note with the picking on which the action
            occurred and a summary on impacted quantity that are
            related to the sale order where the note will be logged.

            :param moves_information dict:
            {'move_id': ['sale_order_line_id', (new_qty, old_qty)], ..}

            :return: an html string with all the information encoded.
            :rtype: str
            """
            origin_moves = self.env["stock.move"].browse(
                [
                    move.id
                    for move_orig in moves_information.values()
                    for move in move_orig[0]
                ],
            )
            origin_picking = origin_moves.mapped("picking_id")
            values = {
                "origin_moves": origin_moves,
                "origin_picking": origin_picking,
                "moves_information": moves_information.values(),
            }
            return self.env["ir.qweb"]._render(
                "sale_stock.exception_on_picking", values
            )

        documents = self.sudo()._log_activity_get_documents(
            moves, "sale_line_id", "DOWN", _keys_in_groupby
        )
        self._log_activity(_render_note_exception_quantity, documents)

        return super(StockPicking, self)._log_less_quantities_than_expected(moves)

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _can_return(self):
        self.ensure_one()
        return super()._can_return() or self.sale_id
