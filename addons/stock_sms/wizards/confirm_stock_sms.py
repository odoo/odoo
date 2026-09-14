from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ConfirmStockSms(models.TransientModel):
    _name = "confirm.stock.sms"
    _description = "Confirm Stock SMS"

    pick_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="stock_picking_sms_rel",
    )

    def send_sms(self):
        _debug.lifecycle("sms_confirmed", wizards=self)
        self.check_singleton()
        for company in self.pick_ids.company_id:
            if not company.has_received_warning_stock_sms:
                company.sudo().write({"has_received_warning_stock_sms": True})
        pickings_to_validate = self.env["stock.picking"].browse(
            self.env.context.get("button_validate_picking_ids")
        )
        return pickings_to_validate.button_validate()

    def dont_send_sms(self):
        _debug.lifecycle("sms_declined", wizards=self)
        self.check_singleton()
        for company in self.pick_ids.company_id:
            if not company.has_received_warning_stock_sms:
                company.sudo().write(
                    {
                        "has_received_warning_stock_sms": True,
                        "stock_text_confirmation": False,
                    }
                )
        pickings_to_validate = self.env["stock.picking"].browse(
            self.env.context.get("button_validate_picking_ids")
        )
        return pickings_to_validate.button_validate()
