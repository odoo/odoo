from odoo import api, models
from odoo.fields import Command, Domain


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings.batch_id._update_picking_type_from_pickings()
        pickings.batch_id._check_pickings_are_allowed()
        return pickings

    def write(self, vals):
        res = super().write(vals)
        if vals.get("batch_id"):
            self.batch_id._update_picking_type_from_pickings()
            self.batch_id._check_pickings_are_allowed()
            if self.batch_id.user_id:
                self.batch_id.picking_ids.update_batch_user(self.batch_id.user_id.id)
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            picking._resolve_auto_batch()
        return res

    def button_validate(self):
        res = super().button_validate()
        to_assign_ids = set()
        if not any(picking.state == "done" for picking in self):
            return res
        if self and self.env.context.get("pickings_to_detach"):
            pickings_to_detach = self.env["stock.picking"].browse(
                self.env.context["pickings_to_detach"]
            )
            pickings_to_detach.batch_id = False
            pickings_to_detach.move_ids.filtered(
                lambda m: not m.quantity
            ).picked = False
            to_assign_ids.update(self.env.context["pickings_to_detach"])

        for picking in self:
            if picking.state != "done":
                continue
            if picking.batch_id and any(
                p.state != "done" for p in picking.batch_id.picking_ids
            ):
                picking.batch_id = None
            to_assign_ids.update(picking.backorder_ids.ids)

        assignable_pickings = self.env["stock.picking"].browse(to_assign_ids)
        for picking in assignable_pickings:
            picking._resolve_auto_batch()
        assignable_pickings.move_line_ids.with_context(
            skip_auto_waveable=True
        )._auto_wave()

        return res

    def _create_backorder(self, backorder_moves=None):
        pickings_to_detach = self.env["stock.picking"].browse(
            self.env.context.get("pickings_to_detach")
        )
        for picking in self:
            if (
                picking.batch_id
                and picking.state != "done"
                and any(
                    p not in self
                    for p in picking.batch_id.picking_ids - pickings_to_detach
                )
            ):
                picking.batch_id = None
        return super()._create_backorder(backorder_moves)

    def _is_transfer_display_required(self):
        detached = self.browse(self.env.context.get("pickings_to_detach"))
        if len(self.batch_id) == 1 and self == self.batch_id.picking_ids - detached:
            return False
        return super()._is_transfer_display_required()

    def _resolve_auto_batch(self):
        self.check_singleton()
        if (
            not self.picking_type_id._is_auto_batch_grouped()
            or self.batch_id
            or not self.move_ids
            or not self._is_auto_batchable()
        ):
            return False

        possible_batches = (
            self.env["stock.picking.batch"]
            .sudo()
            .search(self._get_domain_possible_batches())
        )
        for batch in possible_batches:
            if batch._is_auto_mergeable(**self._get_auto_merge_amounts()):
                batch.picking_ids |= self
                return batch

        possible_pickings = self.env["stock.picking"].search(
            self._get_domain_possible_pickings()
        )
        new_batch_data = {
            "picking_ids": [Command.link(self.id)],
            "company_id": self.company_id.id,
            "picking_type_id": self.picking_type_id.id,
            "description": self._get_auto_batch_description(),
            "user_id": self.user_id.id,
        }
        for picking in possible_pickings:
            if self._is_auto_batchable(picking):
                new_batch_data["picking_ids"].append(Command.link(picking.id))
                break
        new_batch = self.env["stock.picking.batch"].sudo().create(new_batch_data)
        if self.picking_type_id.batch_auto_confirm:
            new_batch.action_confirm()
        return new_batch

    def _get_auto_merge_amounts(self):
        self.check_singleton()
        return {"moves": len(self.move_ids), "pickings": 1}

    def _is_auto_batchable(self, picking=None):
        if self.state != "assigned":
            return False
        res = True
        if not picking:
            picking = self.env["stock.picking"]
        if self.picking_type_id.batch_max_lines:
            res = res and (
                len(self.move_ids) + len(picking.move_ids)
                <= self.picking_type_id.batch_max_lines
            )
        if self.picking_type_id.batch_max_pickings:
            res = res and self.picking_type_id.batch_max_pickings > 1
        return res

    def _get_domain_possible_pickings(self):
        self.check_singleton()
        domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
            ("state", "=", "assigned"),
            ("picking_type_id", "=", self.picking_type_id.id),
            ("batch_id", "=", False),
        ]
        domain.extend(
            (criterion.picking_path, "=", self.mapped(criterion.picking_path).id)
            for criterion in self.picking_type_id._get_active_batch_criteria().values()
        )

        return Domain(domain)

    def _get_domain_possible_batches(self):
        self.check_singleton()
        domain = [
            (
                "state",
                "in",
                ("draft", "in_progress")
                if self.picking_type_id.batch_auto_confirm
                else ("draft",),
            ),
            ("picking_type_id", "=", self.picking_type_id.id),
            ("company_id", "=", self.company_id.id),
            ("is_wave", "=", False),
        ]
        domain.extend(
            (criterion.batch_path, "=", self.mapped(criterion.picking_path).id)
            for criterion in self.picking_type_id._get_active_batch_criteria().values()
        )
        if self.env.context.get("batches_to_validate"):
            domain.append(("id", "not in", self.env.context.get("batches_to_validate")))

        return Domain(domain)

    def _get_auto_batch_description(self):
        self.check_singleton()
        description_items = []
        for criterion in self.picking_type_id._get_active_batch_criteria().values():
            value = self.mapped(criterion.picking_path)
            if value and (label := value[criterion.label_field]):
                description_items.append(label)
        return ", ".join(description_items)

    def _is_single_transfer(self):
        return super()._is_single_transfer() or len(self.batch_id) == 1

    def _add_to_wave_post_picking_split_hook(self):
        pass

    def update_batch_user(self, user_id):
        pickings = self.filtered(lambda p: p.user_id.id != user_id)
        pickings.write({"user_id": user_id})
        for pick in pickings:
            if user_id:
                log_message = self.env._(
                    "Assigned to %s Responsible", pick.batch_id._get_html_link()
                )
            else:
                log_message = self.env._(
                    "Unassigned responsible from %s", pick.batch_id._get_html_link()
                )
            pick.message_post(body=log_message)

    def action_view_batch(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking.batch",
            "res_id": self.batch_id.id,
            "view_mode": "form",
        }

    @api.depends("partner_id")
    @api.depends_context("display_name_partner")
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("display_name_partner"):
            return
        for picking in self.filtered("partner_id"):
            picking.display_name = (
                f"{picking.display_name} - {picking.partner_id.display_name}"
            )
        return
