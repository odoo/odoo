from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_in_ewaybill_ids = fields.One2many(
        comodel_name="l10n.in.ewaybill",
        inverse_name="picking_id",
        string="Ewaybill",
    )
    l10n_in_ewaybill_name = fields.Char(
        string="Indian Ewaybill Number",
        compute="_compute_l10n_in_ewaybill_details",
    )
    l10n_in_ewaybill_feature_enabled = fields.Boolean(
        related="company_id.l10n_in_ewaybill_feature"
    )

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref(
            "l10n_in_ewaybill.l10n_in_ewaybill_form_action"
        )._get_action_dict()

    def action_l10n_in_ewaybill_create(self):
        _debug.pipeline("edi_delivery_send", regime="in", pickings=self)
        self.check_singleton()
        if product_with_no_hsn := self.move_ids.mapped("product_id").filtered(
            lambda p: not p.l10n_in_hsn_code
        ):
            raise UserError(
                _(
                    "Please set HSN code in below products: \n%s",
                    "\n".join(product_with_no_hsn.mapped("name")),
                )
            )
        if self.l10n_in_ewaybill_ids:
            raise UserError(_("Ewaybill already created for this picking."))
        action = self._get_l10n_in_ewaybill_form_action()
        type_xml_trailing_id = (
            "type_delivery_challan_sub_sales_return"
            if self.picking_type_code == "incoming"
            else "type_delivery_challan_sub_others"
        )
        ewaybill = self.env["l10n.in.ewaybill"].create(
            {
                "picking_id": self.id,
                "type_id": self.env.ref(
                    f"l10n_in_ewaybill_stock.{type_xml_trailing_id}"
                ).id,
            }
        )
        action["res_id"] = ewaybill.id
        return action

    def action_view_l10n_in_ewaybill(self):
        self.check_singleton()
        action = self._get_l10n_in_ewaybill_form_action()
        action["res_id"] = self.l10n_in_ewaybill_ids and self.l10n_in_ewaybill_ids[0].id
        return action

    @api.depends("l10n_in_ewaybill_ids.state")
    def _compute_l10n_in_ewaybill_details(self):
        _debug.perf.count("ewaybill_details_compute", pickings=self)
        for picking in self:
            ewaybill = picking.l10n_in_ewaybill_ids and picking.l10n_in_ewaybill_ids[0]
            if picking.country_code == "IN" and ewaybill.state in [
                "challan",
                "generated",
            ]:
                picking.l10n_in_ewaybill_name = ewaybill.name
            else:
                picking.l10n_in_ewaybill_name = False
