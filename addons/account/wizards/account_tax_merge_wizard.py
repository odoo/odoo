import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountTaxMergeWizard(models.TransientModel):
    _name = "account.tax.merge.wizard"
    _inherit = ["mixin.merge"]
    _description = "Tax merge wizard"

    tax_ids = fields.Many2many(comodel_name="account.tax")
    wizard_line_ids = fields.One2many(
        comodel_name="account.tax.merge.wizard.line",
        inverse_name="wizard_id",
        compute="_compute_wizard_line_ids",
        store=True,
        readonly=False,
    )
    disable_merge_button = fields.Boolean(compute="_compute_disable_merge_button")

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields_list)
        if not set(fields_list) & {"tax_ids", "wizard_line_ids"} or set(res) & {
            "tax_ids",
            "wizard_line_ids",
        }:
            return res
        if self.env.context.get("active_model") != "account.tax":
            raise UserError(_("This can only be used on taxes."))
        if len(self.env.context.get("active_ids") or []) < 2:
            raise UserError(_("You must select at least 2 taxes."))
        res["tax_ids"] = [fields.Command.set(self.env.context.get("active_ids"))]
        return res

    @api.model
    def _get_grouping_key(self, tax):
        return (
            tax.name,
            tax.type_tax_use,
            tax.tax_scope,
            tax.country_id,
            tax.amount_type,
            tax.amount,
            tax.price_include_override,
            tax.include_base_amount,
            tax.is_base_affected,
            tax.active,
        )

    @api.model
    def _get_repartition_signature(self, tax):
        return tuple(
            (
                line.document_type,
                line.repartition_type,
                line.factor_percent,
                line.account_id.id,
                tuple(sorted(line.tag_ids.ids)),
            )
            for line in tax.repartition_line_ids.sorted(
                lambda line: (
                    line.document_type,
                    line.repartition_type,
                    line.sequence,
                    line.factor_percent,
                    line.account_id.id or 0,
                )
            )
        )

    @api.depends("tax_ids")
    @_debug.perf.timed
    def _compute_wizard_line_ids(self):
        for wizard in self:
            taxes = wizard.tax_ids._origin
            vals_list = []
            sequence = 0
            for _key, group in taxes.grouped(wizard._get_grouping_key).items():
                vals_list.append(
                    {
                        "display_type": "line_section",
                        "grouping_key": str(_key),
                        "sequence": (sequence := sequence + 1),
                        "tax_id": group[0].id,
                    }
                )
                vals_list.extend(
                    {
                        "display_type": "tax",
                        "grouping_key": str(_key),
                        "sequence": (sequence := sequence + 1),
                        "tax_id": tax.id,
                        "is_selected": True,
                    }
                    for tax in group
                )
            wizard.wizard_line_ids = [fields.Command.clear()] + [
                fields.Command.create(vals) for vals in vals_list
            ]

    @api.depends("wizard_line_ids.is_selected", "wizard_line_ids.info")
    def _compute_disable_merge_button(self):
        for wizard in self:
            selectable = wizard.wizard_line_ids.filtered(
                lambda line: (
                    line.display_type == "tax" and line.is_selected and not line.info
                )
            )
            wizard.disable_merge_button = all(
                len(group) < 2 for group in selectable.grouped("grouping_key").values()
            )

    @_debug.perf.timed
    def action_merge(self):
        _debug.lifecycle("action_merge", records=self)
        for wizard in self:
            selected = wizard.wizard_line_ids.filtered(
                lambda line: (
                    line.display_type == "tax" and line.is_selected and not line.info
                )
            )
            for group in selected.grouped("grouping_key").values():
                if len(group) > 1:
                    self._action_merge(
                        group.sorted("tax_has_hashed_entries", reverse=True).tax_id
                    )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "sticky": False,
                "message": _("Taxes successfully merged!"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_merge_tables_excluded(self, model):
        return super()._get_merge_tables_excluded(model) | {
            self.env["account.tax.repartition.line"]._table
        }

    @api.model
    @_debug.perf.timed
    def _check_access_rights(self, taxes):
        taxes.check_access("write")
        if forbidden := (taxes.sudo().company_ids - self.env.user.company_ids):
            raise UserError(
                _(
                    "You do not have the right to perform this operation as you "
                    "do not have access to the following companies: %s.",
                    ", ".join(company.name for company in forbidden),
                )
            )

    @api.model
    def _repoint_repartition_lines(self, taxes_to_remove, tax_to_merge_into):

        def ordered(tax):
            return tax.repartition_line_ids._sorted_for_positional_pairing()

        destination = ordered(tax_to_merge_into)
        mapping = {}
        for tax in taxes_to_remove:
            for old, new in zip(ordered(tax), destination, strict=True):
                mapping[old.id] = new.id
        if not mapping:
            return
        self.env["account.move.line"].flush_model(["tax_repartition_line_id"])
        self.env.cr.execute(
            SQL(
                """
                UPDATE account_move_line
                   SET tax_repartition_line_id =
                       (%(mapping)s::jsonb->>tax_repartition_line_id::text)::int
                 WHERE tax_repartition_line_id IN %(old_ids)s
                """,
                mapping=json.dumps({str(k): v for k, v in mapping.items()}),
                old_ids=tuple(mapping),
            )
        )
        self.env["account.move.line"].invalidate_model(["tax_repartition_line_id"])

    @api.model
    @_debug.perf.timed
    def _action_merge(self, taxes):
        _debug.lifecycle("_action_merge", records=self)
        company_ids_to_write = taxes.sudo().company_ids
        tax_to_merge_into = taxes[0]
        taxes_to_remove = taxes[1:]
        _debug.pipeline(
            "tax_merge_planned",
            destination=tax_to_merge_into,
            removed=taxes_to_remove,
            companies=company_ids_to_write,
        )

        self._check_access_rights(taxes)
        self._repoint_repartition_lines(taxes_to_remove, tax_to_merge_into)

        self._update_foreign_keys_generic(
            "account.tax", taxes_to_remove, tax_to_merge_into
        )
        self._update_reference_fields_generic(
            "account.tax", taxes_to_remove, tax_to_merge_into
        )

        names = dict(
            self.env.execute_query(
                SQL(
                    "SELECT id, name FROM account_tax WHERE id IN %(ids)s",
                    ids=tuple(taxes.ids),
                )
            )
        )
        _debug.perf.count("tax_names_fetched", rows=len(names))
        merged_name = {}
        for tax_id in taxes.ids[::-1]:
            merged_name.update(names[tax_id] or {})
        _debug.pipeline(
            "tax_names_merged",
            destination=tax_to_merge_into,
            languages=len(merged_name),
        )
        self.env.cr.execute(
            SQL(
                "UPDATE account_tax SET name = %(name)s WHERE id = %(id)s",
                name=json.dumps(merged_name),
                id=tax_to_merge_into.id,
            )
        )

        self.env.invalidate_all()
        self.env.cr.execute(
            SQL(
                "DELETE FROM account_tax WHERE id IN %(ids)s",
                ids=tuple(taxes_to_remove.ids),
            )
        )
        _debug.perf.count("merged_taxes_deleted", rows=self.env.cr.rowcount)
        self.env.registry.clear_cache()
        tax_to_merge_into.sudo().company_ids = company_ids_to_write


class AccountTaxMergeWizardLine(models.TransientModel):
    _name = "account.tax.merge.wizard.line"
    _description = "Tax merge wizard line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="account.tax.merge.wizard",
        required=True,
        ondelete="cascade",
    )
    grouping_key = fields.Char()
    sequence = fields.Integer()
    display_type = fields.Selection(
        selection=[("line_section", "Section"), ("tax", "Tax")],
        required=True,
    )
    is_selected = fields.Boolean()
    tax_id = fields.Many2one(
        comodel_name="account.tax",
        readonly=True,
        ondelete="cascade",
    )
    company_ids = fields.Many2many(related="tax_id.company_ids")
    info = fields.Char(compute="_compute_info")
    tax_has_hashed_entries = fields.Boolean(compute="_compute_tax_has_hashed_entries")

    @api.depends("tax_id")
    @_debug.perf.timed
    def _compute_tax_has_hashed_entries(self):
        query = self.env["account.move.line"]._search(
            [
                "|",
                ("tax_ids", "in", self.tax_id.ids),
                ("tax_line_id", "in", self.tax_id.ids),
                ("move_id.inalterable_hash", "!=", False),
            ],
            bypass_access=True,
        )
        hashed = {
            row[0]
            for row in self.env.execute_query(
                query.select(
                    SQL(
                        "DISTINCT %s",
                        self.env["account.move.line"]._field_to_sql(
                            "account_move_line", "tax_line_id", query
                        ),
                    )
                )
            )
            if row[0]
        }
        _debug.perf.count("hashed_taxes_fetched", rows=len(hashed))
        for line in self:
            line.tax_has_hashed_entries = line.tax_id.id in hashed

    @api.depends("tax_id", "wizard_id.wizard_line_ids.is_selected", "display_type")
    def _compute_info(self):
        for line in self.filtered(lambda l: l.display_type == "line_section"):
            line.info = line.tax_id.display_name
        for group in (
            self.filtered(lambda l: l.display_type == "tax")
            .grouped(lambda l: (l.wizard_id, l.grouping_key))
            .values()
        ):
            group.info = False
            group._update_info_company_conflict()
            group._update_info_repartition_conflict()
            group._update_info_hashed_moves_conflict()

    def _update_info_company_conflict(self):
        seen = self.env["res.company"]
        owner = {}
        for line in self:
            if line.is_selected and not line.info:
                if shared := (line.company_ids & seen):
                    line.info = _(
                        "Serves the same company as %s.",
                        owner[shared[0]].display_name,
                    )
                else:
                    seen |= line.company_ids
                    for company in line.company_ids:
                        owner.setdefault(company, line.tax_id)

    def _update_info_repartition_conflict(self):
        reference = None
        signature_of = self.wizard_id._get_repartition_signature
        for line in self:
            if not line.is_selected or line.info:
                continue
            signature = signature_of(line.tax_id)
            if reference is None:
                reference = (signature, line.tax_id)
            elif signature != reference[0]:
                line.info = _(
                    "Its distribution differs from %s.",
                    reference[1].display_name,
                )

    def _update_info_hashed_moves_conflict(self):
        holder = None
        for line in self:
            if line.is_selected and not line.info and line.tax_has_hashed_entries:
                if holder is None:
                    holder = line.tax_id
                else:
                    line.info = _(
                        "Contains hashed entries, but %s also has hashed entries.",
                        holder.display_name,
                    )
