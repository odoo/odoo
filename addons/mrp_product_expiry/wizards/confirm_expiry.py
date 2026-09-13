from odoo import api, fields, models


class ExpiryPickingConfirmation(models.TransientModel):
    _inherit = "expiry.picking.confirmation"

    production_ids = fields.Many2many(
        comodel_name="mrp.production",
        readonly=True,
    )

    @api.depends("lot_ids", "production_ids")
    def _compute_description(self):
        manufacturing = self.filtered(lambda wizard: wizard.production_ids)
        for wizard in manufacturing:
            if wizard.show_lots:
                wizard.description = self.env._(
                    "You are going to use some expired components."
                    "\nDo you confirm you want to proceed?"
                )
            else:
                wizard.description = self.env._(
                    "You are going to use the component %(product_name)s, %(lot_name)s which is expired."
                    "\nDo you confirm you want to proceed?",
                    product_name=wizard.lot_ids.product_id.display_name,
                    lot_name=wizard.lot_ids.name,
                )
        super(ExpiryPickingConfirmation, self - manufacturing)._compute_description()

    def _get_records_to_confirm(self):
        return self.production_ids or super()._get_records_to_confirm()

    def action_confirm_produce(self):
        self._check_confirm_access("mrp.group_mrp_manager")
        self._log_confirmation_with_expired_lots(self.production_ids)
        return self.production_ids.with_context(
            **self._get_validation_context()
        ).button_mark_done()
