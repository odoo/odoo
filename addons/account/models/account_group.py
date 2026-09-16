from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountGroup(models.Model):
    _name = "account.group"
    _description = "Account Group"
    _order = "code_prefix_start"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.root_id,
        readonly=True,
        required=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    code_prefix_start = fields.Char(
        compute="_compute_code_prefix_start",
        precompute=True,
        store=True,
        readonly=False,
    )
    code_prefix_end = fields.Char(
        compute="_compute_code_prefix_end",
        precompute=True,
        store=True,
        readonly=False,
    )
    parent_id = fields.Many2one(
        comodel_name="account.group",
        index=True,
        readonly=True,
        ondelete="cascade",
        check_company=True,
    )

    _check_length_prefix = models.Constraint(
        "CHECK(char_length(COALESCE(code_prefix_start, '')) "
        "= char_length(COALESCE(code_prefix_end, '')))",
        "The length of the starting and the ending code prefix must be the same",
    )

    @api.constrains("code_prefix_start", "code_prefix_end")
    def _constraint_prefix_overlap(self):
        self.flush_model()
        query = """
            SELECT other.id FROM account_group this
            JOIN account_group other
              ON char_length(other.code_prefix_start)
                 = char_length(this.code_prefix_start)
             AND other.id != this.id
             AND other.company_id = this.company_id
             AND (
                other.code_prefix_start <= this.code_prefix_start
                AND this.code_prefix_start <= other.code_prefix_end
                OR
                other.code_prefix_start >= this.code_prefix_start
                AND this.code_prefix_end >= other.code_prefix_start
            )
            WHERE this.id = ANY(%(ids)s)
        """
        self.env.cr.execute(query, {"ids": list(self.ids)})
        res = self.env.cr.fetchall()
        _debug.perf.count("overlapping_groups_fetched", rows=len(res))
        if res:
            _debug.logic("group_overlap_rejected", groups=self, overlaps=len(res))
            raise ValidationError(
                _("Account Groups with the same granularity can't overlap"),
            )

    @api.constrains("parent_id")
    @_debug.perf.timed
    def _check_parent_not_circular(self):
        if self._has_cycle():
            raise ValidationError(
                _("You cannot create recursive groups."),
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
        groups = super().create([self._normalize_vals(vals) for vals in vals_list])
        groups._adapt_parent_account_group()
        return groups

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        res = super().write(self._normalize_vals(vals))
        if "code_prefix_start" in vals or "code_prefix_end" in vals:
            self._adapt_parent_account_group()
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        children = self.env["account.group"].search(
            [("parent_id", "in", self.ids)],
        )
        for parent, group_children in children.grouped("parent_id").items():
            group_children.parent_id = parent.parent_id.id
        return super().unlink()

    @api.depends("code_prefix_start")
    def _compute_code_prefix_end(self):
        for group in self:
            if not group.code_prefix_end or (
                group.code_prefix_start
                and group.code_prefix_end < group.code_prefix_start
            ):
                group.code_prefix_end = group.code_prefix_start

    @api.depends("code_prefix_end")
    def _compute_code_prefix_start(self):
        for group in self:
            if not group.code_prefix_start or (
                group.code_prefix_end
                and group.code_prefix_start > group.code_prefix_end
            ):
                group.code_prefix_start = group.code_prefix_end

    @api.depends("code_prefix_start", "code_prefix_end")
    def _compute_display_name(self):
        for group in self:
            prefix = group.code_prefix_start and str(group.code_prefix_start)
            if prefix and group.code_prefix_end != group.code_prefix_start:
                prefix += "-" + str(group.code_prefix_end)
            group.display_name = " ".join(
                filter(None, [prefix, group.name]),
            )

    @api.model
    @_debug.perf.timed
    def _search_display_name(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if operator == "in":
            return [
                "|",
                ("code", "in", [(name or "").split(" ")[0] for name in value]),
                ("name", "in", value),
            ]
        if operator == "ilike" and isinstance(value, str):
            return [
                "|",
                ("code_prefix_start", "=ilike", value + "%"),
                ("name", operator, value),
            ]
        return [("name", operator, value)]

    @_debug.perf.timed
    def _adapt_parent_account_group(self, company=None):
        if _debug.logic.enabled and self.env.context.get("delay_account_group_sync"):
            _debug.logic("parent_sync_skipped", reason="delayed", groups=self)
        if self.env.context.get("delay_account_group_sync"):
            return

        company_ids = company.ids if company else self.company_id.ids
        _debug.logic(
            "parent_sync_scope",
            groups=self,
            company=company,
            companies=len(company_ids),
            explicit_company=bool(company),
        )
        if not company_ids:
            return

        # a group's parent is the group with the longest code prefix that still
        # encloses its own, within the same company; a company's groups number in
        # the hundreds, so the match is made in Python rather than a self-join
        updated = 0
        Group = self.env["account.group"].sudo().with_context(active_test=False)
        groups_by_company = Group.search([("company_id", "in", company_ids)]).grouped(
            "company_id"
        )
        for groups in groups_by_company.values():
            candidates = [
                group
                for group in groups
                if group.code_prefix_start and group.code_prefix_end
            ]
            for child in groups:
                start, end = child.code_prefix_start, child.code_prefix_end
                enclosing = [
                    parent
                    for parent in candidates
                    if parent != child
                    and start
                    and end
                    and len(parent.code_prefix_start) < len(start)
                    and parent.code_prefix_start
                    <= start[: len(parent.code_prefix_start)]
                    and parent.code_prefix_end >= end[: len(parent.code_prefix_end)]
                ]
                parent = (
                    max(enclosing, key=lambda p: (len(p.code_prefix_start), -p.id))
                    if enclosing
                    else Group.browse()
                )
                if child.parent_id != parent:
                    child.parent_id = parent
                    updated += 1
        _debug.perf.count("group_parents_relinked", rows=updated)

    def _normalize_vals(self, vals):
        vals = dict(vals)
        if (
            vals.get("code_prefix_start")
            and "code_prefix_end" in vals
            and not vals["code_prefix_end"]
        ):
            del vals["code_prefix_end"]
        if (
            vals.get("code_prefix_end")
            and "code_prefix_start" in vals
            and not vals["code_prefix_start"]
        ):
            del vals["code_prefix_start"]
        return vals
