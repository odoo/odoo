from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

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
        groups = super().create([self._sanitize_vals(vals) for vals in vals_list])
        groups._adapt_parent_account_group()
        return groups

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        res = super().write(self._sanitize_vals(vals))
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

        self.flush_model()
        query = SQL(
            """
            WITH relation AS (
                SELECT DISTINCT ON (child.id)
                       child.id AS child_id,
                       parent.id AS parent_id
                  FROM account_group parent
            RIGHT JOIN account_group child
                    ON char_length(parent.code_prefix_start)
                       < char_length(child.code_prefix_start)
                   AND parent.code_prefix_start
                       <= LEFT(child.code_prefix_start,
                               char_length(parent.code_prefix_start))
                   AND parent.code_prefix_end
                       >= LEFT(child.code_prefix_end,
                               char_length(parent.code_prefix_end))
                   AND parent.id != child.id
                   AND parent.company_id = child.company_id
                 WHERE child.company_id = ANY(%s)
              ORDER BY child.id,
                       char_length(parent.code_prefix_start) DESC
            )
            UPDATE account_group child
               SET parent_id = relation.parent_id
              FROM relation
             WHERE child.id = relation.child_id
               AND child.parent_id IS DISTINCT FROM relation.parent_id
         RETURNING child.id
            """,
            list(company_ids),
        )
        self.env.cr.execute(query)

        updated_rows = self.env.cr.fetchall()
        _debug.perf.count("group_parents_relinked", rows=len(updated_rows))
        if updated_rows:
            self.invalidate_model(["parent_id"])

    def _sanitize_vals(self, vals):
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
