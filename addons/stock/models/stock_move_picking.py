import logging

from odoo import api, models
from odoo.fields import Domain
from odoo.tools.misc import OrderedSet, groupby
from odoo.tools.translate import _

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class StockMovePicking(models.Model):
    _inherit = "stock.move"

    @dbg.timed
    def _update_picking(self):
        # the pickings the groups need are created together, then every group
        # is attached and post-processed in one pass per kind: a picking's
        # creation posts to its chatter, and mail batches what it is given
        Picking = self.env["stock.picking"]
        grouped_moves = [
            self.env["stock.move"].concat(*moves)
            for _group, moves in groupby(
                self, key=lambda m: m._get_picking_assignation_key()
            )
        ]
        picking_by_lead = self._get_pickings_for_assignation(
            [moves[0] for moves in grouped_moves]
        )
        existing = []
        wanted = []
        for moves in grouped_moves:
            picking = picking_by_lead[moves[0]]
            if picking:
                vals = moves._prepare_picking_vals(picking)
                if vals:
                    picking.write(vals)
                existing.append((moves, picking))
            else:
                moves = moves.filtered(
                    lambda m: m.product_uom_id.compare(m.product_uom_qty, 0.0) >= 0,
                )
                if not moves:
                    dbg.logic.debug("_update_picking: only negative moves, no picking")
                    continue
                pending = moves._pending_picking_for_assignation(wanted)
                if pending is None:
                    wanted.append([moves])
                else:
                    pending.append(moves)
        created = Picking.create(
            [groups[0]._prepare_new_picking_vals() for groups in wanted]
        )
        for groups, picking in zip(wanted, created, strict=True):
            for joining in groups[1:]:
                vals = joining._prepare_picking_vals(picking)
                if vals:
                    picking.write(vals)
        for new_picking, pairs in (
            (False, existing),
            (
                True,
                (
                    (self.env["stock.move"].concat(*groups), picking)
                    for groups, picking in zip(wanted, created, strict=True)
                ),
            ),
        ):
            attached = self.env["stock.move"]
            for moves, picking in pairs:
                dbg.pipeline.debug(
                    "_update_picking: %s -> picking %s (%s)",
                    dbg.rec(moves),
                    picking.id,
                    "new" if new_picking else "existing",
                )
                moves.write({"picking_id": picking.id})
                attached |= moves
            if attached:
                attached._post_process_picking(new=new_picking)
        return True

    def _pending_picking_for_assignation(self, wanted):
        if not self.reference_ids:
            return None
        first = self[0]
        reference_set = set(first.reference_ids.ids)
        covered = None

        for groups in wanted:
            lead = groups[0][0]
            if (
                lead.location_id != first.location_id
                or lead._get_picking_destination() != first._get_picking_destination()
                or lead.picking_type_id != first.picking_type_id
            ):
                continue
            pending_set = set().union(*(set(g.reference_ids.ids) for g in groups))
            if not pending_set & reference_set:
                continue
            if pending_set == reference_set:
                return groups
            if covered is None and pending_set <= reference_set:
                covered = groups
        return covered

    def _get_picking_destination(self):
        return self.location_dest_id or self.picking_type_id.default_location_dest_id

    def _prepare_picking_vals(self, picking):
        vals = {}
        if any(picking.partner_id != m.partner_id for m in self):
            vals["partner_id"] = False
        if any(picking.origin != m.origin for m in self):
            current_origins = picking.origin.split(",") if picking.origin else []
            new_moves_origins = [move.origin for move in self if move.origin]
            new_origin = ",".join(OrderedSet(current_origins + new_moves_origins))
            if picking.origin != new_origin:
                vals["origin"] = new_origin
        return vals

    def _post_process_picking(self, new=False):
        pass

    def _prepare_new_picking_vals(self):
        origins = list(dict.fromkeys(self.filtered("origin").mapped("origin")))
        origin = ",".join(origins[:5]) if origins else False
        if origins and len(origins) > 5:
            origin += "..."
        partners = self.partner_id
        vals = {
            "origin": origin,
            "company_id": self.company_id.id,
            "user_id": False,
            "partner_id": partners.id if len(partners) == 1 else False,
            "picking_type_id": self.picking_type_id.id,
            "location_id": self.location_id.id,
        }
        if self.location_dest_id:
            vals["location_dest_id"] = self.location_dest_id.id
        return vals

    def _get_picking_assignation_key(self):
        self.check_singleton()
        keys = (
            self.reference_ids,
            self.location_id,
            self.location_dest_id,
            self.picking_type_id,
            self.company_id,
        )
        if self.move_orig_ids.picking_id and not self.reference_ids:
            keys += (self.move_orig_ids.picking_id,)
        return keys

    def _get_domain_picking_for_assignation(self):
        return [
            ("reference_ids", "in", self.reference_ids.ids),
            ("location_id", "=", self.location_id.id),
            (
                "location_dest_id",
                "=",
                (
                    self.location_dest_id.id
                    or self.picking_type_id.default_location_dest_id.id
                ),
            ),
            ("picking_type_id", "=", self.picking_type_id.id),
            ("printed", "=", False),
            (
                "state",
                "in",
                ["draft", "confirmed", "waiting", "partially_available", "assigned"],
            ),
        ]

    def _get_picking_for_assignation(self):
        self.check_singleton()
        return self._get_pickings_for_assignation([self])[self]

    @api.model
    def _get_pickings_for_assignation(self, leads):
        Picking = self.env["stock.picking"]
        domains = {
            lead: lead._get_domain_picking_for_assignation()
            for lead in leads
            if lead.reference_ids
        }
        candidates = Picking.search(Domain.OR(domains.values())) if domains else Picking
        return {
            lead: (
                lead._pick_picking_for_assignation(candidates.filtered_domain(domain))
                if (domain := domains.get(lead)) is not None
                else Picking
            )
            for lead in leads
        }

    def _pick_picking_for_assignation(self, candidates):
        reference_set = set(self.reference_ids.ids)
        covered_picking = self.env["stock.picking"]
        for picking in candidates:
            picking_set = set(picking.reference_ids.ids)
            if picking_set == reference_set:
                dbg.logic.debug(
                    "[move:%s] picking %s matches references exactly",
                    self.id,
                    picking.id,
                )
                return picking
            if not covered_picking and picking_set <= reference_set:
                covered_picking = picking
        dbg.logic.debug(
            "[move:%s] _get_picking_for_assignation: covered picking %s",
            self.id,
            covered_picking.id,
        )
        return covered_picking

    def _update_references(self):
        to_set = self.filtered(lambda m: not m.reference_ids and m.picking_id)
        for picking, moves in to_set.grouped("picking_id").items():
            if picking.reference_ids:
                dbg.lifecycle.debug(
                    "_update_references: %s inherit references of picking %s",
                    dbg.rec(moves),
                    picking.id,
                )
                moves.reference_ids = picking.reference_ids

    def action_view_reference(self):
        self.check_singleton()
        if (
            not self.is_inventory
            and self.location_dest_usage == "inventory"
            and self.scrap_id
        ):
            return {
                "res_model": "stock.scrap",
                "type": "ir.actions.act_window",
                "views": [[False, "form"]],
                "res_id": self.scrap_id.id,
            }
        source = self.picking_id
        if source and source.has_access("read"):
            return {
                "res_model": source._name,
                "type": "ir.actions.act_window",
                "views": [[False, "form"]],
                "res_id": source.id,
            }
        return {
            "res_model": self._name,
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_id": self.id,
        }

    def action_show_details(self):
        self.check_singleton()
        view = self.env.ref("stock.view_stock_move_form_operations")

        return {
            "name": _("Detailed Operations"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.move",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
            "context": dict(
                self.env.context,
                default_picked=self.picked,
            ),
        }

    def action_product_forecast_report(self):
        self.check_singleton()
        action = self.product_id.action_product_forecast_report()
        action["context"] = {
            "active_id": self.product_id.id,
            "active_model": "product.product",
            "move_to_match_ids": self.ids,
        }
        if self._is_consuming():
            warehouse = self.location_id.warehouse_id
        else:
            warehouse = self.location_dest_id.warehouse_id

        if warehouse:
            action["context"]["warehouse_id"] = warehouse.id
        return action

    def _get_description(self):
        product = self.product_id.with_context(lang=self._get_lang())
        return product._get_description(self.picking_type_id)

    def _get_partner_id(self):
        self.check_singleton()
        if self.location_id == self.company_id.internal_transit_location_id:
            return self.location_dest_id.warehouse_id.partner_id.id
        return self.partner_id.id

    def _get_lang(self):
        return (
            self.picking_id.partner_id.lang
            or self.partner_id.lang
            or self.env.user.lang
        )

    def _get_source_document(self):
        self.check_singleton()
        return self.picking_id or False

    def _get_report_description_picking(self):
        self.check_singleton()
        description = self.description_picking or ""
        if description.startswith(self.product_id.display_name):
            description = description.removeprefix(self.product_id.display_name).strip()
        return description

    def _get_product_catalog_lines_data(self, parent_record=False, **kwargs):
        if not (parent_record and self):
            return {
                "quantity": 0,
            }
        self.product_id.check_singleton()
        return {
            **parent_record._get_product_price_and_data(self.product_id),
            "quantity": (
                self.product_uom_qty
                if len(self) == 1
                else sum(self.mapped("product_qty"))
            ),
            "readOnly": len(self) > 1,
            "uomDisplayName": (len(self) == 1 and self.product_uom_id.display_name)
            or self.product_id.uom_id.display_name,
        }

    def _log_cancel_activity(self):
        return
