from odoo import fields, models

from ..tools import debug_log as dbg


class ResPartner(models.Model):
    _inherit = "res.partner"
    _check_company_auto = True

    property_stock_customer = fields.Many2one(
        comodel_name="stock.location",
        string="Customer Location",
        company_dependent=True,
        domain="[('company_id', 'in', [False, allowed_company_ids[0]])]",
        check_company=True,
        help="The stock location used as destination when sending goods to this contact.",
    )
    property_stock_supplier = fields.Many2one(
        comodel_name="stock.location",
        string="Vendor Location",
        company_dependent=True,
        domain="[('company_id', 'in', [False, allowed_company_ids[0]])]",
        check_company=True,
        help="The stock location used as source when receiving goods from this contact.",
    )
    picking_warn_msg = fields.Text(string="Message for Stock Picking")

    def _update_stock_property_locations(self, location):
        dbg.lifecycle.debug(
            "_update_stock_property_locations: partners %s -> location %s (company %s)",
            dbg.rec(self),
            location.id,
            self.env.company.id,
        )
        self.write(
            {
                "property_stock_customer": location.id,
                "property_stock_supplier": location.id,
            },
        )

    def action_view_stock_serial(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "stock.action_stock_lot_form",
        )
        action["domain"] = [("partner_ids", "child_of", self.ids)]
        action["context"] = {"display_complete": True}
        return action
