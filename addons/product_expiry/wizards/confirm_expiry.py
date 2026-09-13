from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class ExpiryPickingConfirmation(models.TransientModel):
    _name = "expiry.picking.confirmation"
    _description = "Confirm Expiry"

    lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        readonly=True,
        required=True,
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        readonly=True,
    )
    description = fields.Char(compute="_compute_description")
    show_lots = fields.Boolean(compute="_compute_show_lots")

    @api.depends("lot_ids")
    def _compute_show_lots(self):
        for wizard in self:
            wizard.show_lots = len(wizard.lot_ids) > 1

    @api.depends("lot_ids")
    def _compute_description(self):
        for wizard in self:
            if wizard.show_lots:
                wizard.description = self.env._(
                    "You are going to deliver some product expired lots."
                    "\nDo you confirm you want to proceed?"
                )
            else:
                wizard.description = self.env._(
                    "You are going to deliver the product %(product_name)s, %(lot_name)s which is expired or should at least be removed from stock."
                    "\nDo you confirm you want to proceed?",
                    product_name=wizard.lot_ids.product_id.display_name,
                    lot_name=wizard.lot_ids.name,
                )

    def _get_pickings_to_validate(self):
        return self.env["stock.picking"].browse(
            self.env.context.get("button_validate_picking_ids") or []
        )

    def _get_validation_context(self):
        return {
            key: value
            for key, value in self.env.context.items()
            if not key.startswith("default_")
        } | {"skip_expired": True}

    def _check_confirm_access(self, group_xmlid):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(
                self.env._(
                    "Only a manager can confirm %(records)s with expired lots.",
                    records=", ".join(self._get_records_to_confirm().mapped("name")),
                )
            )

    def _get_records_to_confirm(self):
        return self._get_pickings_to_validate()

    def _log_confirmation_with_expired_lots(self, records):
        body = self.env._(
            "%(user)s confirmed using expired lot(s): %(lots)s.",
            user=self.env.user.name,
            lots=", ".join(self.lot_ids.mapped("name")),
        )
        records._message_log_batch(bodies=dict.fromkeys(records.ids, body))

    def process(self):
        pickings = self._get_pickings_to_validate()
        if not pickings:
            return True
        self._check_confirm_access("stock.group_stock_manager")
        self._log_confirmation_with_expired_lots(pickings)
        return pickings.with_context(**self._get_validation_context()).button_validate()

    def process_no_expired(self):
        pickings = self._get_pickings_to_validate()
        self.picking_ids.move_line_ids._filtered_expired().unlink()
        remaining = pickings.filtered("move_line_ids")
        emptied = pickings - remaining
        if emptied:
            raise UserError(
                self.env._(
                    "Every line of %(pickings)s is expired, so there is nothing left to"
                    " deliver. Cancel the transfer, or replace the expired lots before"
                    " validating it.",
                    pickings=", ".join(emptied.mapped("name")),
                )
            )
        return remaining.button_validate()
