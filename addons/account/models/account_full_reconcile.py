from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Reconcile"

    partial_reconcile_ids = fields.One2many(
        comodel_name="account.partial.reconcile",
        inverse_name="full_reconcile_id",
        string="Reconciliation Parts",
    )
    reconciled_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="full_reconcile_id",
        string="Matched Journal Items",
    )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )

        def get_ids(commands):
            for command in commands:
                if command[0] == Command.LINK:
                    yield command[1]
                elif command[0] == Command.SET:
                    yield from command[2]
                else:
                    raise ValueError("Unexpected command: %s" % command)

        move_line_ids = [
            list(get_ids(vals.pop("reconciled_line_ids"))) for vals in vals_list
        ]
        partial_ids = [
            list(get_ids(vals.pop("partial_reconcile_ids"))) for vals in vals_list
        ]
        fulls = super(
            AccountFullReconcile, self.with_context(tracking_disable=True)
        ).create(vals_list)
        _debug.pipeline(
            "created_over_group_group",
            full=fulls,
            move_line_ids_count=len(move_line_ids),
            partial_ids_count=len(partial_ids),
        )

        self.env.cr.execute_values(
            """
            UPDATE account_move_line line
               SET full_reconcile_id = source.full_id
              FROM (VALUES %s) AS source(full_id, line_ids)
             WHERE line.id = ANY(source.line_ids)
            """,
            [
                (full.id, line_ids)
                for full, line_ids in zip(fulls, move_line_ids, strict=True)
            ],
            page_size=1000,
        )
        if _debug.perf.enabled:
            _debug.perf.count(
                "full_lines_linked", rows=sum(len(ids) for ids in move_line_ids)
            )
        fulls.reconciled_line_ids.invalidate_recordset(
            ["full_reconcile_id"], flush=False
        )
        fulls.invalidate_recordset(["reconciled_line_ids"], flush=False)

        self.env.cr.execute_values(
            """
            UPDATE account_partial_reconcile partial
               SET full_reconcile_id = source.full_id
              FROM (VALUES %s) AS source(full_id, partial_ids)
             WHERE partial.id = ANY(source.partial_ids)
            """,
            [
                (full.id, line_ids)
                for full, line_ids in zip(fulls, partial_ids, strict=True)
            ],
            page_size=1000,
        )
        if _debug.perf.enabled:
            _debug.perf.count(
                "full_partials_linked", rows=sum(len(ids) for ids in partial_ids)
            )
        fulls.partial_reconcile_ids.invalidate_recordset(
            ["full_reconcile_id"], flush=False
        )
        fulls.invalidate_recordset(["partial_reconcile_ids"], flush=False)

        self.env["account.partial.reconcile"]._update_matching_number(
            fulls.reconciled_line_ids
        )
        return fulls

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        amls = self.reconciled_line_ids
        res = super().unlink()
        if self.env.context.get("defer_matching_number_update"):
            _debug.logic("full_unlink_matching_number_update")
            return res
        amls = amls.exists()
        if amls:
            self.env["account.partial.reconcile"]._update_matching_number(amls)
        return res
