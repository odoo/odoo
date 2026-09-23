from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingToBatch(models.TransientModel):
    _name = "stock.picking.to.batch"
    _description = "Batch Transfer Lines"

    batch_id = fields.Many2one(
        comodel_name="stock.picking.batch",
        string="Batch Transfer",
        domain="[('is_wave', '=', False), ('state', 'in', ('draft', 'in_progress'))]",
    )
    mode = fields.Selection(
        selection=[
            ("existing", "an existing batch transfer"),
            ("new", "a new batch transfer"),
        ],
        default="new",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
    )
    is_create_draft = fields.Boolean(
        string="Draft",
        help="When checked, create the batch in draft status",
    )
    description = fields.Char()

    def attach_pickings(self):
        self.check_singleton()
        pickings = self.env["stock.picking"].browse(self.env.context.get("active_ids"))
        _debug.pipeline(
            "picking_to_batch",
            mode=self.mode,
            pickings=pickings,
            batch=self.batch_id,
            draft=self.is_create_draft,
        )
        if not pickings:
            raise UserError(self.env._("Select the transfers to add to a batch."))
        if self.mode == "new":
            company = pickings.company_id
            if len(company) > 1:
                raise UserError(
                    self.env._(
                        "The selected transfers should belong to a unique company."
                    )
                )
            batch = self.env["stock.picking.batch"].create(
                {
                    "user_id": self.user_id.id,
                    "company_id": company.id,
                    "picking_type_id": pickings[0].picking_type_id.id,
                    "description": self.description,
                }
            )
            notification_title = self.env._(
                "The following batch transfer has been created"
            )
        else:
            batch = self.batch_id
            if not batch:
                raise UserError(
                    self.env._("Choose the batch transfer to add the transfers to.")
                )
            notification_title = self.env._(
                "The following batch transfer has been updated"
            )

        pickings.write({"batch_id": batch.id})
        if self.mode == "new" and not self.is_create_draft:
            batch.action_confirm()
        return batch._get_notification_action(notification_title)
