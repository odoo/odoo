from odoo import api, fields, models


class MixinResourceScheduling(models.AbstractModel):
    _name = "mixin.resource.scheduling"
    _description = "Resource Scheduling Mixin"
    _inherit = ["mixin.resource.scheduling.tools"]

    _reservation_sync_manual = False

    reservation_ids = fields.One2many(
        comodel_name="resource.reservation",
        inverse_name="res_id",
        string="Reservations",
        copy=False,
        domain=lambda self: [("res_model", "=", self._name)],
        bypass_search_access=True,
    )
    schedule_overlap_count = fields.Integer(
        string="Scheduling Conflicts",
        compute="_compute_schedule_overlap_count",
        search="_search_schedule_overlap_count",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self._reservation_sync_manual:
            records._active_for_sync()._sync_reservations()
        return records

    def write(self, vals):
        result = super().write(vals)
        start_field, end_field = self._get_fields_reservation_date()
        has_dates = bool(start_field and end_field)
        reactivating = bool(vals.get("active")) and has_dates

        if "active" in vals and has_dates and not reactivating:
            mirror_active = bool(vals["active"])
            self.env["resource.reservation"].sudo().with_context(
                active_test=False
            ).search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                    ("active", "!=", mirror_active),
                ]
            ).write({"active": mirror_active})

        triggers = self._get_fields_sync_trigger()
        sync_needed = bool(triggers and triggers.intersection(vals.keys()))
        if (sync_needed or reactivating) and not self._reservation_sync_manual:
            self._active_for_sync()._sync_reservations()
        return result

    def unlink(self):
        model_name, record_ids = self._name, self.ids
        result = super().unlink()
        self.env["resource.reservation"].sudo().with_context(active_test=False).search(
            [
                ("res_model", "=", model_name),
                ("res_id", "in", record_ids),
            ]
        ).unlink()
        return result

    @api.depends(lambda self: self._get_fields_overlap_depends())
    def _compute_schedule_overlap_count(self):
        stored = self.filtered(lambda record: isinstance(record.id, int))
        for record in stored:
            record.schedule_overlap_count = sum(
                record.reservation_ids.mapped("schedule_overlap_count")
            )
        for record in self - stored:
            record.schedule_overlap_count = len(record._get_schedule_conflicts())

    @api.model
    def _search_schedule_overlap_count(self, operator, value):
        if not isinstance(value, int) or value != 0 or operator not in ("=", "!="):
            return NotImplemented
        conflicted = (
            self.env["resource.reservation"]
            .sudo()
            .search(
                [("res_model", "=", self._name), ("schedule_overlap_count", ">", 0)]
            )
        )
        record_ids = list({reservation.res_id for reservation in conflicted})
        return [("id", "not in" if operator == "=" else "in", record_ids)]

    def _get_fields_reservation_date(self):
        return (None, None)

    def _get_fields_sync_trigger(self):
        triggers = set()
        start_field, end_field = self._get_fields_reservation_date()
        if start_field:
            triggers.add(start_field)
        if end_field:
            triggers.add(end_field)
        return triggers

    def _get_fields_overlap_depends(self):
        return [
            "reservation_ids.schedule_overlap_count",
            "reservation_ids.active",
            *sorted(self._get_fields_sync_trigger()),
        ]

    def _get_schedule_conflicts(self):
        self.check_singleton()
        return self._get_schedule_conflicts_batch()[self.id]

    def _get_schedule_conflicts_batch(self):
        reservation_model = self.env["resource.reservation"].sudo()
        empty = reservation_model.browse()
        result = dict.fromkeys(self._ids, empty)

        stored = self.filtered(lambda record: isinstance(record.id, int))
        own_by_record = {record.id: record.reservation_ids.sudo() for record in stored}
        all_own = empty
        for own in own_by_record.values():
            all_own |= own
        if all_own:
            partners = all_own._conflicting_reservations()
            for record_id, own in own_by_record.items():
                found = empty
                for reservation in own:
                    found |= partners.get(reservation.id, empty)
                result[record_id] = found - own

        for record in self - stored:
            result[record.id] = reservation_model._prospective_conflicts(
                record._prepare_reservation_vals_list(),
                ignore_ids=record._origin.reservation_ids.ids,
            )
        return result

    def _prepare_reservation_vals_list(self):
        self.check_singleton()
        return []

    def _sync_reservations(self):
        start_field, end_field = self._get_fields_reservation_date()
        if not start_field or not end_field or not self:
            return
        reservation_model = self.env["resource.reservation"]
        existing_all = (
            reservation_model.sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                ]
            )
        )
        existing_by_record = existing_all.grouped("res_id")
        no_reservations = existing_all.browse()
        for record in self:
            reservation_model._sync_projection(
                record,
                record._prepare_reservation_vals_list(),
                existing=existing_by_record.get(record.id, no_reservations),
            )
        self.invalidate_recordset(["reservation_ids", "schedule_overlap_count"])

    def _active_for_sync(self):
        if "active" in self._fields:
            return self.filtered("active")
        return self

    def _is_scheduling_dated(self):
        start_field, end_field = self._get_fields_reservation_date()
        return bool(start_field and end_field and self[start_field] and self[end_field])
