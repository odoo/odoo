import math

from odoo import api, models
from odoo.tools import OrderedSet
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_picking import DONE_CANCEL_STATES
from odoo.addons.web.controllers.utils import clean_action


class StockPickingReport(models.Model):
    _inherit = "stock.picking"

    def action_print_picking(self):
        return self.env.ref("stock.action_report_picking").report_action(self)

    @dbg.timed
    def _attach_signed_delivery_slip(self):
        self.check_singleton()
        dbg.pipeline.debug("[picking:%s] rendering signed delivery slip", self.name)
        report = self.env["ir.actions.report"]._render_qweb_pdf(
            "stock.action_report_delivery",
            self.id,
        )
        filename = "%s_signed_delivery_slip" % self.name
        if self.partner_id:
            message = _("Order signed by %s", self.partner_id.name)
        else:
            message = _("Order signed")
        self.message_post(
            attachments=[("%s.pdf" % filename, report[0])],
            body=message,
        )
        return True

    def _prepare_action_autoprint(self, report_xmlid, records, data=None):
        if not records:
            return None
        action = self.env.ref(report_xmlid).report_action(
            records,
            data=data,
            config=False,
        )
        clean_action(action, self.env)
        return action

    def _autoprint_delivery_slip(self):
        action = self._prepare_action_autoprint(
            "stock.action_report_delivery",
            self.filtered(lambda p: p.picking_type_id.auto_print_delivery_slip),
        )
        return [action] if action else []

    def _autoprint_return_slip(self):
        action = self._prepare_action_autoprint(
            "stock.return_label_report",
            self.filtered(lambda p: p.picking_type_id.auto_print_return_slip),
        )
        return [action] if action else []

    def _autoprint_reception_reports(self):
        if not self.env.user.has_group("stock.group_reception_report"):
            return []
        actions = []
        report_action = self._prepare_action_autoprint(
            "stock.stock_reception_report_action",
            self.filtered(
                lambda p: (
                    p.picking_type_id.auto_print_reception_report
                    and p.picking_type_id.code != "outgoing"
                    and p.move_ids.move_dest_ids
                ),
            ),
        )
        if report_action:
            actions.append(report_action)
        reception_labels_to_print = self.filtered(
            lambda p: (
                p.picking_type_id.auto_print_reception_report_labels
                and p.picking_type_id.code != "outgoing"
            ),
        )
        moves_to_print = reception_labels_to_print.move_ids.move_dest_ids
        if moves_to_print:
            quantities = ",".join(
                str(qty)
                for qty in moves_to_print.mapped(
                    lambda m: math.ceil(m.product_uom_qty),
                )
            )
            label_action = self._prepare_action_autoprint(
                "stock.label_picking",
                moves_to_print,
                data={"docids": moves_to_print.ids, "quantity": quantities},
            )
            if label_action:
                actions.append(label_action)
        return actions

    def _autoprint_product_labels(self):
        actions = []
        pickings_print_product_label = self.filtered(
            lambda p: p.picking_type_id.auto_print_product_labels,
        )
        for print_format, pickings in pickings_print_product_label.grouped(
            lambda p: p.picking_type_id.product_label_format,
        ).items():
            wizard = self.env["product.label.layout"].create(
                {
                    "product_ids": pickings.move_ids.product_id.ids,
                    "move_ids": pickings.move_ids.ids,
                    "move_quantity": "move",
                    "print_format": print_format,
                },
            )
            action = wizard.process()
            if action:
                clean_action(action, self.env)
                actions.append(action)
        return actions

    def _autoprint_lot_labels(self):
        if not self.env.user.has_group("stock.group_production_lot"):
            return []
        actions = []
        pickings_print_lot_label = self.filtered(
            lambda p: (
                p.picking_type_id.auto_print_lot_labels and p.move_line_ids.lot_id
            ),
        )
        for print_format, pickings in pickings_print_lot_label.grouped(
            lambda p: p.picking_type_id.lot_label_format,
        ).items():
            wizard = self.env["lot.label.layout"].create(
                {
                    "move_line_ids": pickings.move_line_ids.ids,
                    "label_quantity": "lots" if "_lots" in print_format else "units",
                    "print_format": "4x12" if "4x12" in print_format else "zpl",
                },
            )
            action = wizard.process()
            if action:
                clean_action(action, self.env)
                actions.append(action)
        return actions

    def _autoprint_package_report(self):
        if not self.env.user.has_group("stock.group_tracking_lot"):
            return []
        action = self._prepare_action_autoprint(
            "stock.action_report_picking_packages",
            self.filtered(
                lambda p: (
                    p.picking_type_id.auto_print_packages
                    and p.move_line_ids.result_package_id
                ),
            ),
        )
        return [action] if action else []

    @dbg.timed
    def _prepare_actions_autoprint(self):
        actions = [
            *self._autoprint_delivery_slip(),
            *self._autoprint_return_slip(),
            *self._autoprint_reception_reports(),
            *self._autoprint_product_labels(),
            *self._autoprint_lot_labels(),
            *self._autoprint_package_report(),
        ]
        dbg.logic.debug(
            "_prepare_actions_autoprint on %s: %s",
            dbg.rec(self),
            [action.get("report_name") or action.get("name") for action in actions],
        )
        return actions

    def _get_packages_for_print(self):
        package_ids = OrderedSet()
        for picking in self:
            if picking.state == "done":
                package_ids.update(picking.package_history_ids.package_id.ids)
            else:
                package_ids.update(
                    picking.move_line_ids.result_package_id._get_all_package_dest_ids(),
                )
        return self.env["stock.package"].browse(package_ids)

    def _get_report_lang(self):
        self.check_singleton()
        return (
            (self.move_ids and self.move_ids[0].partner_id.lang)
            or self.partner_id.lang
            or self.env.lang
        )

    @dbg.timed
    def _get_reception_report_action(self):
        if not self.env.user.has_group("stock.group_reception_report"):
            return False
        pickings_show_report = self.filtered(
            lambda p: p.picking_type_id.auto_show_reception_report,
        )
        Move = self.env["stock.move"]
        has_allocatable_demand = False
        for warehouse, pickings in pickings_show_report.grouped(
            lambda p: p.picking_type_id.warehouse_id,
        ).items():
            lines = pickings.move_ids.filtered(
                lambda m: (
                    m.product_id.is_storable
                    and m.state != "cancel"
                    and m.quantity
                    and not m.move_dest_ids
                ),
            )
            if not lines:
                continue
            wh_location_ids = self.env["stock.location"]._get_allocation_source_ids(
                warehouse.view_location_id.ids,
            )
            if Move.search_count(  # noqa: E8507 - already batched per warehouse, and the loop breaks on the first hit
                [
                    *Move._get_domain_allocatable_demand(
                        wh_location_ids,
                        lines.product_id.ids,
                    ),
                    ("move_orig_ids", "=", False),
                    ("picking_id", "not in", pickings_show_report.ids),
                ],
                limit=1,
            ):
                has_allocatable_demand = True
                dbg.logic.debug(
                    "_get_reception_report_action: allocatable demand in warehouse %s",
                    warehouse.id,
                )
                break
        if not has_allocatable_demand:
            return False
        action = pickings_show_report.action_view_reception_report()
        action["context"] = {"default_picking_ids": pickings_show_report.ids}
        return action

    def action_view_reception_report(self):
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_reception_action",
        )

    def action_view_label_layout(self):
        view = self.env.ref("stock.product_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "res_model": "product.label.layout",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_product_ids": self.move_ids.product_id.ids,
                "default_move_ids": self.move_ids.ids,
                "default_move_quantity": "move",
            },
        }

    def action_view_label_type(self):
        if (
            self.env.user.has_group("stock.group_production_lot")
            and self.move_line_ids.lot_id
        ):
            view = self.env.ref("stock.picking_label_type_form")
            return {
                "name": _("Choose Type of Labels To Print"),
                "type": "ir.actions.act_window",
                "res_model": "picking.label.type",
                "views": [(view.id, "form")],
                "target": "new",
                "context": {"default_picking_ids": self.ids},
            }
        return self.action_view_label_layout()

    def is_delivery_address_print_required(self):
        self.check_singleton()
        return bool(
            self.move_ids
            and (self.move_ids[0].partner_id or self.partner_id)
            and self._is_to_external_location(),
        )

    def action_view_move_scrap(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_scrap"
        )
        action["domain"] = [("picking_id", "=", self.id)]
        action["context"] = dict(self.env.context, create=False)
        return action

    def action_view_packages(self):
        self.check_singleton()
        return {
            "name": self.env._("Packages"),
            "res_model": "stock.package",
            "view_mode": "list,kanban,form",
            "views": [
                (self.env.ref("stock.view_stock_package_list_editable").id, "list"),
                (False, "kanban"),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "domain": [("picking_ids", "in", self.ids)],
            "context": {
                "picking_ids": self.ids,
                "location_id": self.location_id.id,
                "can_add_entire_packs": self.picking_type_code != "incoming",
                "search_default_main_packages": True,
            },
        }

    def action_view_package_histories(self):
        self.check_singleton()
        return {
            "name": self.env._("Packages"),
            "res_model": "stock.package.history",
            "view_mode": "list",
            "views": [(False, "list")],
            "type": "ir.actions.act_window",
            "domain": [("picking_ids", "=", self.id)],
            "context": {
                "search_default_main_packages": 1,
            },
        }

    def action_view_move_list(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_move_action"
        )
        action["views"] = [
            (self.env.ref("stock.view_stock_move_list_picking").id, "list"),
        ]
        action["context"] = self.env.context
        action["domain"] = [("picking_id", "in", self.ids)]
        return action

    def action_view_returns(self):
        self.check_singleton()
        return self._prepare_action_pickings(self.return_ids, _("Returns"))

    @api.model
    def _prepare_action_pickings(self, pickings, name):
        if len(pickings) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id": pickings.id,
            }
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("id", "in", pickings.ids)],
        }

    @api.model
    def action_view_pickings_incoming(self):
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_incoming",
        )

    @api.model
    def action_view_pickings_outgoing(self):
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_outgoing",
        )

    @api.model
    def action_view_pickings_internal(self):
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_internal",
        )

    @api.model
    def get_action_click_graph(self):
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_graph",
        )

    @api.model
    def get_empty_list_help(self, help_message):
        if not self.env.context.get("restricted_picking_type_code"):
            return super().get_empty_list_help(help_message)
        return self._render_picking_help()

    def _render_picking_help(self):
        return self.env["ir.ui.view"]._render_template(
            "stock.help_message_template",
            {
                "picking_type_code": self.env.context.get(
                    "restricted_picking_type_code"
                )
                or self.picking_type_code,
            },
        )

    def action_detailed_operations(self):
        view_id = self.env.ref("stock.view_stock_move_line_detailed_operation_tree").id
        return {
            "name": _("Detailed Operations"),
            "view_mode": "list",
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "views": [(view_id, "list")],
            "domain": [("picking_id", "=", self.id)],
            "context": {
                "sml_specific_default": True,
                "default_picking_id": self.id,
                "default_location_id": self.location_id.id,
                "default_location_dest_id": self.location_dest_id.id,
                "default_company_id": self.company_id.id,
                "show_lots_text": self.show_lots_text,
                "picking_code": self.picking_type_code,
                "create": self.state not in DONE_CANCEL_STATES,
            },
        }

    def action_next_transfer(self):
        return self._prepare_action_pickings(
            self._get_next_transfers(), _("Next Transfers")
        )

    def _get_next_transfers(self):
        return self.move_ids.move_dest_ids.picking_id - self.return_ids
