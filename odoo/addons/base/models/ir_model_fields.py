import contextlib
import logging
import re
from ast import literal_eval
from collections import defaultdict
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.db import schema as sql
from odoo.exceptions import UserError, ValidationError
from odoo.fields import NO_ACCESS, Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import get_index_name
from odoo.models import pop_field
from odoo.tools import SQL, OrderedSet, frozendict, unique
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import FIELD_TRANSLATE, _

from .ir_model_common import (
    MODULE_UNINSTALL_FLAG,
    compute_modules,
    field_xmlid,
    mark_modified,
    prepare_compute,
    reload_schema,
    select_en,
    upsert_en,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


RELATIONAL_TTYPES = frozenset({"many2one", "one2many", "many2many"})
type ColumnRename = tuple[str, str, str, bool, bool] | None
TRANSLATE_KEY_BY_HANDLER = {handler: key for key, handler in FIELD_TRANSLATE.items()}


def _selection_field_types(_model) -> list[tuple[str, str]]:
    return [(key, key) for key in sorted(fields.Field._by_type__)]


def _check_translate_value(vals: dict[str, Any]) -> None:
    if vals.get("translate") and not isinstance(vals["translate"], str):
        raise ValidationError(
            _(
                "The translation mode is a selection since Odoo 19: pass "
                "'standard', 'html_translate' or 'xml_translate' instead of "
                "%(value)s.",
                value=repr(vals["translate"]),
            )
        )


class IrModelFields(models.Model):
    _name = "ir.model.fields"
    _is_registry_metadata = True
    _description = "Fields"
    _order = "name, id"
    _rec_name = "field_description"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Field Name",
        default="x_",
        index=True,
        required=True,
    )
    model = fields.Char(
        string="Model Name",
        index=True,
        required=True,
        help="The technical name of the model this field belongs to",
    )
    relation = fields.Char(
        string="Related Model",
        help="For relationship fields, the technical name of the target model",
    )
    relation_field = fields.Char(
        help="For one2many fields, the field on the target model that implement the opposite many2one relationship"
    )
    relation_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Relation field",
        compute="_compute_relation_field_id",
        store=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
        help="The model this field belongs to",
    )
    field_description = fields.Char(
        string="Field Label",
        translate=True,
        default="",
        required=True,
    )
    help = fields.Text(
        string="Field Help",
        translate=True,
    )
    ttype = fields.Selection(
        selection=_selection_field_types,
        string="Field Type",
        required=True,
    )
    selection = fields.Char(
        string="Selection Options (Deprecated)",
        compute="_compute_selection",
        inverse="_inverse_selection",
    )
    selection_ids = fields.One2many(
        comodel_name="ir.model.fields.selection",
        inverse_name="field_id",
        string="Selection Options",
        copy=True,
    )
    copied = fields.Boolean(
        compute="_compute_copied",
        store=True,
        readonly=False,
        help="Whether the value is copied when duplicating a record.",
    )
    related = fields.Char(
        string="Related Field Definition",
        help="The corresponding related field, if any. This must be a dot-separated list of field names.",
    )
    related_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        compute="_compute_related_field_id",
        store=True,
        ondelete="cascade",
    )
    required = fields.Boolean()
    readonly = fields.Boolean()
    index = fields.Boolean(string="Indexed")
    translate = fields.Selection(
        selection=[
            ("standard", "Translate as a whole"),
            ("html_translate", "Translate HTML terms"),
            ("xml_translate", "Translate XML terms"),
        ],
        string="Translatable",
        help="Whether values for this field can be translated (enables the translation mechanism for that field)",
    )
    company_dependent = fields.Boolean(
        readonly=True,
        help="Whether values for this field is company dependent",
    )
    size = fields.Integer()
    state = fields.Selection(
        selection=[("manual", "Custom Field"), ("base", "Base Field")],
        string="Type",
        default="manual",
        index=True,
        readonly=True,
        required=True,
    )
    on_delete = fields.Selection(
        selection=[
            ("cascade", "Cascade"),
            ("set null", "Set NULL"),
            ("restrict", "Restrict"),
        ],
        default="set null",
        help="On delete property for many2one fields",
    )
    domain = fields.Char(
        default="[]",
        help="The optional domain to restrict possible values for relationship fields, "
        "specified as a Python expression defining a list of triplets. "
        "For example: [('color','=','red')]",
    )
    groups = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_model_fields_group_rel",
        column1="field_id",
        column2="group_id",
        string="Restricted to Groups",
        help="Groups allowed to read and write this field.  Only honoured for "
        "manual (custom) fields: a base field's restriction is declared in "
        "Python and reflected from the code, not from this table.  Each group "
        "needs an external id to be enforceable.",
    )
    group_expand = fields.Boolean(
        string="Expand Groups",
        help="If checked, all the records of the target model will be included\n"
        "in a grouped result (e.g. 'Group By' filters, Kanban columns, etc.).\n"
        "Note that it can significantly reduce performance if the target model\n"
        "of the field contains a lot of records; usually used on models with\n"
        "few records (e.g. Stages, Job Positions, Event Types, etc.).",
    )
    selectable = fields.Boolean(default=True)
    modules = fields.Char(
        string="In Apps",
        compute="_compute_modules",
        help="List of modules in which the field is defined",
    )
    relation_table = fields.Char(
        help="Used for custom many2many fields to define a custom relation table name"
    )
    column1 = fields.Char(
        string="Column 1",
        help="Column referring to the record in the model table",
    )
    column2 = fields.Char(
        string="Column 2",
        help="Column referring to the record in the comodel table",
    )
    compute = fields.Text(
        help="Code to compute the value of the field.\n"
        "Iterate on the recordset 'self' and assign the field's value:\n\n"
        "    for record in self:\n"
        "        record['size'] = len(record.name)\n\n"
        "Modules time, datetime, dateutil are available."
    )
    depends = fields.Char(
        string="Dependencies",
        help="Dependencies of compute method; a list of comma-separated field names, like\n\n    name, partner_id.name",
    )
    store = fields.Boolean(
        string="Stored",
        default=True,
        help="Whether the value is stored in the database.",
    )
    currency_field = fields.Char(
        string="Currency field",
        help="Name of the Many2one field holding the res.currency",
    )
    sanitize = fields.Boolean(
        string="Sanitize HTML",
        default=True,
    )
    sanitize_overridable = fields.Boolean(
        string="Sanitize HTML overridable",
        default=False,
    )
    sanitize_tags = fields.Boolean(
        string="Sanitize HTML Tags",
        default=True,
    )
    sanitize_attributes = fields.Boolean(
        string="Sanitize HTML Attributes",
        default=True,
    )
    sanitize_style = fields.Boolean(
        string="Sanitize HTML Style",
        default=False,
    )
    sanitize_form = fields.Boolean(
        string="Sanitize HTML Form",
        default=True,
    )
    strip_style = fields.Boolean(
        string="Strip Style Attribute",
        default=False,
    )
    strip_classes = fields.Boolean(
        string="Strip Class Attribute",
        default=False,
    )

    @api.depends("state", "relation", "relation_field")
    def _compute_relation_field_id(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.relation_field:
                rec.relation_field_id = self._get(rec.relation, rec.relation_field)
            else:
                rec.relation_field_id = False

    @api.depends("state", "related")
    def _compute_related_field_id(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.related:
                rec.related_field_id = rec._get_related_target_field()
            else:
                rec.related_field_id = False

    @api.depends("ttype", "selection_ids.value", "selection_ids.name")
    def _compute_selection(self) -> None:
        for rec in self:
            if rec.ttype in ("selection", "reference"):
                rec.selection = str(
                    [(sel.value, sel.name) for sel in rec.selection_ids]
                )
            else:
                rec.selection = False

    def _inverse_selection(self) -> None:
        for rec in self:
            selection = literal_eval(rec.selection or "[]")
            _debug.lifecycle(
                "selection.inverse",
                model=rec.model,
                field=rec.name,
                count=len(selection),
            )
            self.env["ir.model.fields.selection"]._update_selection(
                rec.model, rec.name, selection
            )

    @api.depends("ttype", "related", "compute")
    def _compute_copied(self) -> None:
        for rec in self:
            rec.copied = (rec.ttype != "one2many") and not (rec.related or rec.compute)

    @api.depends()
    def _compute_modules(self) -> None:
        compute_modules(self)

    @api.constrains("domain")
    def _check_domain(self) -> None:
        for field in self:
            try:
                safe_eval(field.domain or "[]")
            except (ValueError, SyntaxError) as e:
                _debug.logic(
                    "constraint.rejected",
                    model=field.model,
                    field=field.name,
                    reason="domain_unparseable",
                )
                raise ValidationError(
                    _(
                        "An error occurred while evaluating the domain:\n%(error)s",
                        error=e,
                    )
                ) from e

    @api.constrains("name")
    def _check_name(self) -> None:
        for field in self:
            try:
                models.check_column_name(field.name)
            except ValidationError as e:
                _debug.logic(
                    "constraint.rejected",
                    model=field.model,
                    field=field.name,
                    reason="invalid_name",
                )
                raise ValidationError(
                    _(
                        "Field names can only contain characters, digits and underscores (up to 63)."
                    )
                ) from e

    _name_unique = models.Constraint(
        "UNIQUE(model, name)", "Field names must be unique per model."
    )
    _size_gt_zero = models.Constraint(
        "CHECK (size>=0)", "Size of the field cannot be negative."
    )
    _name_manual_field = models.Constraint(
        "CHECK (state != 'manual' OR name LIKE 'x\\_%')",
        "Custom fields must have a name that starts with 'x_'!",
    )

    def _get_related_target_field(self) -> Self:
        names = self.related.split(".")
        last = len(names) - 1
        model_name = self.model or self.model_id.model
        for index, name in enumerate(names):
            field = self._get(model_name, name)
            if not field:
                _debug.logic(
                    "related.rejected",
                    related=self.related,
                    step=name,
                    reason="unknown_field",
                )
                raise ValidationError(
                    _(
                        'Unknown field name "%(field_name)s" in related field "%(related_field)s"',
                        field_name=name,
                        related_field=self.related,
                    )
                )
            model_name = field.relation
            if index < last and not field.relation:
                _debug.logic(
                    "related.rejected",
                    related=self.related,
                    step=name,
                    reason="non_relational",
                )
                raise ValidationError(
                    _(
                        'Non-relational field name "%(field_name)s" in related field "%(related_field)s"',
                        field_name=name,
                        related_field=self.related,
                    )
                )
            if index < last and not field.store:
                _debug.logic(
                    "related.rejected",
                    related=self.related,
                    step=name,
                    reason="not_stored",
                )
                raise ValidationError(
                    _(
                        'Field "%(field_name)s" in related path "%(related_field)s" is not '
                        "stored. Non-stored fields cannot be used in related fields.",
                        field_name=name,
                        related_field=self.related,
                    )
                )
        return field

    @api.constrains("related")
    def _check_related(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.related:
                field = rec._get_related_target_field()
                if field.ttype != rec.ttype:
                    _debug.logic(
                        "related.rejected", related=rec.related, reason="type_mismatch"
                    )
                    raise ValidationError(
                        _(
                            'Related field "%(related_field)s" does not have type "%(type)s"',
                            related_field=rec.related,
                            type=rec.ttype,
                        )
                    )
                if field.relation != rec.relation:
                    _debug.logic(
                        "related.rejected",
                        related=rec.related,
                        reason="comodel_mismatch",
                    )
                    raise ValidationError(
                        _(
                            'Related field "%(related_field)s" does not have comodel "%(comodel)s"',
                            related_field=rec.related,
                            comodel=rec.relation,
                        )
                    )

    @api.onchange("related")
    def _onchange_related(self) -> dict[str, Any] | None:
        if self.related:
            try:
                field = self._get_related_target_field()
            except ValidationError as e:
                _debug.logic("onchange_related.warning", related=self.related)
                return {"warning": {"title": _("Warning"), "message": e}}
            _debug.logic(
                "onchange_related.applied",
                related=self.related,
                ttype=field.ttype,
                relation=field.relation,
            )
            self.ttype = field.ttype
            self.relation = field.relation
            self.readonly = True
        return None

    @api.onchange("relation")
    def _onchange_relation(self) -> dict[str, Any] | None:
        try:
            self._check_relation()
        except ValidationError as e:
            return {
                "warning": {
                    "title": _("Model %s does not exist", self.relation),
                    "message": e,
                }
            }

    @api.constrains("relation")
    def _check_relation(self) -> None:
        for rec in self:
            if (
                rec.state == "manual"
                and rec.relation
                and not rec.env["ir.model"]._get_id(rec.relation)
            ):
                _debug.logic(
                    "constraint.rejected",
                    field=rec.name,
                    relation=rec.relation,
                    reason="unknown_relation",
                )
                raise ValidationError(
                    _("Unknown model name '%s' in Related Model", rec.relation)
                )

    @api.constrains("ttype", "relation", "relation_field", "store")
    def _check_relational_definition(self) -> None:
        for rec in self:
            if rec.state != "manual" or rec.ttype not in RELATIONAL_TTYPES:
                continue
            if not rec.relation:
                _debug.logic(
                    "constraint.rejected",
                    field=rec.name,
                    ttype=rec.ttype,
                    reason="relation_missing",
                )
                raise ValidationError(
                    _(
                        "The %(type)s field \u201c%(field)s\u201d has no Related "
                        "Model. A relational field cannot be built without one.",
                        type=rec.ttype,
                        field=rec.name,
                    )
                )
            if rec.ttype == "one2many" and rec.store and not rec.relation_field:
                _debug.logic(
                    "constraint.rejected",
                    field=rec.name,
                    reason="relation_field_missing",
                )
                raise ValidationError(
                    _(
                        "The stored one2many field \u201c%(field)s\u201d has no "
                        "Relation Field. Name the many2one on %(comodel)s that "
                        "points back to %(model)s, or clear Stored.",
                        field=rec.name,
                        comodel=rec.relation,
                        model=rec.model,
                    )
                )

    @api.constrains("depends", "compute")
    def _check_depends(self) -> None:
        for record in self:
            if not record.depends:
                continue
            if record.state == "manual" and not record.compute:
                _debug.logic("depends.rejected", field=record.name, reason="no_compute")
                raise ValidationError(
                    _(
                        "Dependencies are only read for a computed field, so "
                        "\u201c%(dependency)s\u201d on \u201c%(field)s\u201d would "
                        "never be applied. Give the field a compute method or "
                        "clear its dependencies.",
                        dependency=record.depends,
                        field=record.name,
                    )
                )
            base_model = self.env.get(record.model)
            if base_model is None:
                _debug.logic(
                    "depends.rejected",
                    field=record.name,
                    model=record.model,
                    reason="model_not_in_registry",
                )
                raise ValidationError(
                    _(
                        "Cannot check the dependencies of \u201c%(field)s\u201d: "
                        "its model %(model)s is not in the registry.",
                        field=record.name,
                        model=record.model,
                    )
                )
            for raw_seq in record.depends.split(","):
                seq = raw_seq.strip()
                if not seq:
                    raise ValidationError(
                        _("Empty dependency in \u201c%s\u201d", record.depends)
                    )
                model = base_model
                names = seq.split(".")
                last = len(names) - 1
                for index, name in enumerate(names):
                    if name == "id":
                        raise ValidationError(
                            _("Compute method cannot depend on field 'id'")
                        )
                    field = model._fields.get(name)
                    if field is None:
                        _debug.logic(
                            "depends.rejected",
                            field=record.name,
                            dependency=seq,
                            step=name,
                            reason="unknown_field",
                        )
                        raise ValidationError(
                            _(
                                "Unknown field \u201c%(field)s\u201d in dependency \u201c%(dependency)s\u201d",
                                field=name,
                                dependency=seq,
                            )
                        )
                    if index == last:
                        break
                    if not field.relational:
                        _debug.logic(
                            "depends.rejected",
                            field=record.name,
                            dependency=seq,
                            step=name,
                            reason="non_relational",
                        )
                        raise ValidationError(
                            _(
                                "Non-relational field \u201c%(field)s\u201d in dependency \u201c%(dependency)s\u201d",
                                field=name,
                                dependency=seq,
                            )
                        )
                    model = model[name]

    @api.onchange("compute")
    def _onchange_compute(self) -> None:
        if self.compute:
            self.readonly = True

    @api.constrains("relation_table")
    def _check_relation_table(self) -> None:
        for rec in self:
            if rec.relation_table:
                try:
                    models.check_pg_name(rec.relation_table)
                except ValidationError as e:
                    raise ValidationError(
                        _(
                            "Relation table names can only contain characters, digits and underscores (up to 63)."
                        )
                    ) from e

    @api.constrains("currency_field")
    def _check_currency_field(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.ttype == "monetary":
                if not rec.currency_field:
                    currency_field = self._get(rec.model, "currency_id") or self._get(
                        rec.model, "x_currency_id"
                    )
                    if not currency_field:
                        _debug.logic(
                            "currency_field.rejected",
                            model=rec.model,
                            field=rec.name,
                            reason="no_fallback",
                        )
                        raise ValidationError(
                            _(
                                "Currency field is empty and there is no fallback field in the model"
                            )
                        )
                else:
                    currency_field = self._get(rec.model, rec.currency_field)
                    if not currency_field:
                        _debug.logic(
                            "currency_field.rejected",
                            model=rec.model,
                            field=rec.name,
                            currency_field=rec.currency_field,
                            reason="unknown",
                        )
                        raise ValidationError(
                            _(
                                "Unknown field specified \u201c%s\u201d in currency_field",
                                rec.currency_field,
                            )
                        )

                if currency_field.ttype != "many2one":
                    _debug.logic(
                        "currency_field.rejected",
                        model=rec.model,
                        field=rec.name,
                        reason="not_many2one",
                    )
                    raise ValidationError(
                        _("Currency field does not have type many2one")
                    )
                if currency_field.relation != "res.currency":
                    _debug.logic(
                        "currency_field.rejected",
                        model=rec.model,
                        field=rec.name,
                        reason="not_res_currency",
                    )
                    raise ValidationError(
                        _("Currency field should have a res.currency relation")
                    )

    @api.model
    def _get_custom_many2many_names(
        self, model_name: str, comodel_name: str
    ) -> tuple[str, str, str]:
        rel1 = self.env[model_name]._table
        rel2 = self.env[comodel_name]._table
        s1, s2 = sorted([rel1, rel2])
        table = f"x_{s1}_{s2}_rel"
        if rel1 == rel2:
            return (table, "id1", "id2")
        else:
            return (table, f"{rel1}_id", f"{rel2}_id")

    @api.onchange("ttype", "model_id", "relation")
    def _onchange_relation_definition(self) -> None:
        if self.ttype == "many2many" and self.model_id and self.relation:
            if self.relation not in self.env:
                _debug.logic(
                    "onchange_relation_definition.skipped",
                    relation=self.relation,
                    reason="unknown_comodel",
                )
                return
            names = self._get_custom_many2many_names(self.model_id.model, self.relation)
            _debug.logic("onchange_relation_definition.derived", table=names[0])
            self.relation_table, self.column1, self.column2 = names
        else:
            self.relation_table = False
            self.column1 = False
            self.column2 = False

    @api.onchange("relation_table")
    def _onchange_relation_table(self) -> dict[str, Any] | None:
        if self.relation_table:
            others = self.search(
                [
                    ("ttype", "=", "many2many"),
                    ("relation_table", "=", self.relation_table),
                    ("id", "not in", self.ids),
                ]
            )
            if others:
                for other in others:
                    if (other.model, other.relation) == (
                        self.relation,
                        self.model,
                    ):
                        _debug.logic(
                            "relation_table.shared",
                            table=self.relation_table,
                            other=other.id,
                            reason="inverse_pair",
                        )
                        self.column1 = other.column2
                        self.column2 = other.column1
                        return None
                _debug.logic(
                    "relation_table.shared",
                    table=self.relation_table,
                    others=len(others),
                    reason="incompatible",
                )
                return {
                    "warning": {
                        "title": _("Warning"),
                        "message": _(
                            "The table \u201c%s\u201d is used by another, possibly incompatible field(s).",
                            self.relation_table,
                        ),
                    }
                }
        return None

    @api.constrains("required", "ttype", "on_delete")
    def _check_on_delete_required_m2o(self) -> None:
        for rec in self:
            if rec.ttype == "many2one" and rec.required and rec.on_delete == "set null":
                _debug.logic(
                    "constraint.rejected", field=rec.name, reason="required_set_null"
                )
                raise ValidationError(
                    _(
                        "The m2o field %s is required but declares its ondelete policy "
                        "as being 'set null'. Only 'restrict' and 'cascade' make sense.",
                        rec.name,
                    )
                )

    def _get(self, model_name: str, name: str) -> Self:
        field_id = (
            self._get_ids_by_name(model_name).get(name) if model_name and name else None
        )
        return self.sudo().browse(field_id or ())

    @tools.ormcache("model_name", cache="stable")
    def _get_ids_by_name(self, model_name: str) -> dict[str, int]:
        fields_ = self.sudo().search_fetch([("model", "=", model_name)], ["name"])
        _debug.perf.count(
            "ids_by_name.cache_miss", model=model_name, fields=len(fields_)
        )
        return {field.name: field.id for field in fields_}

    def _drop_columns(self) -> bool:
        cr = self.env.cr
        columns_by_table = defaultdict(OrderedSet)
        for field in self:
            if field.name in models.MAGIC_COLUMNS:
                continue
            model = self.env.get(field.model)
            if model is None:
                _debug.logic(
                    "drop_columns.skipped",
                    model=field.model,
                    field=field.name,
                    reason="model_not_in_registry",
                )
                continue
            if field.store:
                columns_by_table[model._table].add(field.name)
            if field.state == "manual":
                pop_field(self.env.registry[model._name], field.name)

        for table, names in columns_by_table.items():
            if sql.get_table_kind(cr, table) != sql.TableKind.Regular:
                _debug.logic("drop_columns.skipped", table=table, reason="not_regular")
                continue
            dropped = sql.drop_columns(cr, table, names)
            _debug.lifecycle("drop_columns", table=table, columns=dropped)

        self._drop_m2m_tables()
        return True

    def _drop_m2m_tables(self) -> None:
        tables_to_drop = set()
        for field in self:
            if not field.store or field.state != "manual":
                continue
            if field.ttype != "many2many":
                continue
            rel_name = field.relation_table or self._get_m2m_table_name(field)
            if rel_name:
                tables_to_drop.add(rel_name)
            else:
                _debug.logic(
                    "drop_m2m_tables.unresolved", model=field.model, field=field.name
                )
                _logger.warning(
                    "Cannot determine the relation table of %s.%s; its "
                    "many2many table is left in the database",
                    field.model,
                    field.name,
                )
        if not tables_to_drop:
            return

        self.env.cr.execute(
            """SELECT relation_table FROM ir_model_fields
               WHERE relation_table = ANY(%s) AND id != ALL(%s)""",
            (list(tables_to_drop), list(self.ids)),
        )
        tables_to_keep = {row[0] for row in self.env.cr.fetchall()}
        _debug.lifecycle(
            "drop_m2m_tables",
            drop=sorted(tables_to_drop - tables_to_keep),
            keep=sorted(tables_to_keep),
        )
        for rel_name in tables_to_drop - tables_to_keep:
            self.env.cr.execute(
                SQL("DROP TABLE IF EXISTS %s", SQL.identifier(rel_name))
            )

    def _get_views_mentioning(self, field_names: list[str]) -> models.BaseModel:
        if not field_names:
            _debug.logic("views_mentioning.skipped", reason="no_field_names")
            return self.env["ir.ui.view"].browse()
        View = self.env["ir.ui.view"]
        View.flush_model(["arch_db"])
        pattern = r"\y(%s)\y" % "|".join(sorted(map(re.escape, set(field_names))))
        view_ids = [
            row[0]
            for row in self.env.execute_query(
                SQL(
                    "SELECT id FROM %s WHERE EXISTS ("
                    " SELECT 1 FROM jsonb_each_text(arch_db) AS t(lang, arch)"
                    " WHERE t.arch ~ %s)",
                    SQL.identifier(View._table),
                    pattern,
                )
            )
        ]
        _debug.perf.count(
            "views_mentioning.scanned", fields=len(field_names), views=len(view_ids)
        )
        return View.search([("id", "in", view_ids)])

    def _get_m2m_table_name(self, field: Self) -> str | None:
        model = self.env.get(field.model)
        registry_field = None if model is None else model._fields.get(field.name)
        if registry_field is not None:
            return registry_field.relation
        if model is not None and field.relation in self.env:
            return self._get_custom_many2many_names(field.model, field.relation)[0]
        return None

    def _prepare_update(self, setup_models: bool = True) -> Self:
        uninstalling = self.env.context.get(MODULE_UNINSTALL_FLAG)
        requested = {(record.model, record.name) for record in self}
        if not uninstalling and any(
            self._is_module_data(record, requested) for record in self
        ):
            _debug.logic("prepare_update.rejected", reason="base_field")
            raise UserError(
                _("This column contains module data and cannot be removed!")
            )

        records, failed_dependencies = self._get_dependent_fields_and_failures()
        self = records
        _debug.logic(
            "prepare_update",
            fields=len(records),
            failed_dependencies=len(failed_dependencies),
            uninstalling=bool(uninstalling),
            setup_models=setup_models,
        )

        if failed_dependencies:
            if not uninstalling:
                field, dep = failed_dependencies[0]
                _debug.logic(
                    "prepare_update.rejected",
                    field=field.name,
                    dependent=dep.name,
                    reason="manual_dependent",
                )
                raise UserError(
                    _(
                        "The field '%(field)s' cannot be removed because the field '%(other_field)s' depends on it.",
                        field=field,
                        other_field=dep,
                    )
                )
            self = self.union(
                *[
                    self._get(dep.model_name, dep.name)
                    for field, dep in failed_dependencies
                ]
            )

        records = self.filtered(
            lambda record: record.state == "manual" and record.model in self.pool
        )
        if not records:
            _debug.logic("prepare_update.no_registry_fields", fields=len(self))
            return self

        for record in records:
            field = self.env[record.model]._fields.get(record.name)
            if field:
                self.env.core.pop_dirty(field)
        fields_ = [
            pop_field(self.env.registry[record.model], record.name)
            for record in records
        ]
        self.pool.discard_fields([field for field in fields_ if field is not None])
        views = self._get_views_mentioning(records.mapped("name"))
        _debug.logic("views_mentioning_fields", fields=len(records), views=len(views))
        try:
            for view in views:
                view._check_xml()
        except Exception:
            _debug.logic(
                "prepare_update.view_broken",
                view=view.id,
                uninstalling=bool(uninstalling),
            )
            if not uninstalling:
                self.pool.setup_models(self.env.cr, OrderedSet(records.mapped("model")))
                raise UserError(
                    _(
                        "Cannot rename/delete fields that are still present in views:\nFields: %(fields)s\nView: %(view)s",
                        fields=fields_,
                        view=view.name,
                    )
                ) from None
            _logger.warning(
                "The following fields were force-deleted to prevent a registry crash %s the following view might be broken %s",
                ", ".join(str(f) for f in fields_),
                view.name,
            )
        if not uninstalling and setup_models:
            with _debug.perf(
                "prepare_update.setup_models",
                cr=self.env.cr,
                models=sorted(set(records.mapped("model"))),
            ):
                self.pool.setup_models(self.env.cr, OrderedSet(records.mapped("model")))

        return self

    def _get_attachments_of_binary_fields(self) -> models.BaseModel:
        Attachment = self.env["ir.attachment"].sudo()
        binaries = self.filtered(
            lambda record: record.ttype == "binary" and record.model
        )
        if not binaries:
            return Attachment
        domain = Domain.OR(
            Domain("res_model", "=", model)
            & Domain("res_field", "in", records.mapped("name"))
            for model, records in binaries.grouped("model").items()
        )
        attachments = Attachment.search(domain)
        _debug.perf.count(
            "binary_attachments.found",
            fields=len(binaries),
            attachments=len(attachments),
        )
        return attachments

    def _rename_attachments_of_binary_field(self, old_name: str) -> None:
        self.check_singleton()
        attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", self.model), ("res_field", "=", old_name)])
        )
        _debug.lifecycle(
            "binary_attachments.renamed",
            model=self.model,
            old=old_name,
            new=self.name,
            count=len(attachments),
        )
        if attachments:
            attachments.write({"res_field": self.name})

    def _is_module_data(self, record: Self, requested: set[tuple[str, str]]) -> bool:
        # an inherited copy of a manual field goes with its base field, never alone
        if record.state == "manual":
            return False
        model = self.env.get(record.model)
        field = model._fields.get(record.name) if model is not None else None
        if field is None or not field.inherited:
            return True
        base = field.base_field
        return not (base.manual and (base.model_name, base.name) in requested)

    def _get_dependent_fields_and_failures(self) -> tuple[Self, list[tuple]]:
        records = self
        fields_ = OrderedSet()
        failed_dependencies = []

        requested = OrderedSet()
        for record in self:
            model = self.env.get(record.model)
            if model is not None and (field := model._fields.get(record.name)):
                requested.add(field)

        for field in list(requested):
            fields_.add(field)
            for dep in self.pool.get_dependent_fields(field):
                if dep in requested:
                    continue
                if dep.manual:
                    failed_dependencies.append((field, dep))
                elif dep.inherited:
                    fields_.add(dep)
                    records |= self._get(dep.model_name, dep.name)

        for field in fields_:
            failed_dependencies.extend(
                (field, inverse)
                for inverse in self.pool.field_inverses[field]
                if inverse.manual and inverse.type == "one2many"
            )

        _debug.logic(
            "dependent_fields.resolved",
            requested=len(self),
            records=len(records),
            registry_fields=len(fields_),
            failed=len(failed_dependencies),
        )
        return records, failed_dependencies

    def unlink(self) -> bool:
        if not self:
            _debug.logic("unlink.skipped", reason="empty_recordset")
            return True

        self = self._prepare_update()

        fields_ = OrderedSet()
        for record in self:
            with contextlib.suppress(KeyError):
                fields_.add(self.pool[record.model]._fields[record.name])

        self.pool.registry_invalidated = True
        self.pool.discard_fields(fields_)

        for field in fields_:
            self.env.core.discard_field(field)

        model_names = OrderedSet(self.mapped("model"))
        uninstalling = self.env.context.get(MODULE_UNINSTALL_FLAG)
        _debug.lifecycle(
            "unlink",
            fields=[f"{r.model}.{r.name}" for r in self],
            registry_fields=len(fields_),
            uninstalling=bool(uninstalling),
        )
        if not uninstalling:
            self._get_attachments_of_binary_fields().unlink()
        self._drop_columns()
        res = super().unlink()

        if not uninstalling:
            with _debug.perf("reload_schema", cr=self.env.cr, models=list(model_names)):
                reload_schema(self.env, model_names, model_names)

        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        IrModel = self.env["ir.model"]
        vals_list = [dict(vals) for vals in vals_list]

        model_ids = OrderedSet(
            vals["model_id"] for vals in vals_list if vals.get("model_id")
        )
        model_by_id = {model.id: model.model for model in IrModel.browse(model_ids)}

        inverses_wanted = OrderedSet()
        inverses_in_batch = set()
        for vals in vals_list:
            _check_translate_value(vals)
            if "model_id" in vals:
                vals["model"] = model_by_id.get(vals["model_id"], False)
            if vals.get("ttype") == "many2one" and vals.get("name"):
                inverses_in_batch.add((vals.get("model"), vals["name"]))
            if vals.get("state", "manual") != "manual":
                continue
            if (relation := vals.get("relation")) and not IrModel._get_id(relation):
                _debug.logic(
                    "create.rejected",
                    field=vals.get("name"),
                    relation=relation,
                    reason="unknown_relation",
                )
                raise UserError(_("Model %s does not exist!", relation))
            if (
                vals.get("ttype") == "one2many"
                and vals.get("store", True)
                and not vals.get("related")
                and vals.get("relation_field")
            ):
                inverses_wanted.add((vals["relation"], vals["relation_field"]))

        inverses_wanted = OrderedSet(
            pair for pair in inverses_wanted if pair not in inverses_in_batch
        )
        if inverses_wanted:
            self._check_inverses_exist(inverses_wanted)

        self.env.registry.clear_cache("stable")
        res = super().create(vals_list)
        res._add_missing_group_xml_ids()

        model_names = OrderedSet(res.mapped("model"))
        _debug.lifecycle(
            "create",
            count=len(res),
            models=list(model_names),
            manual=sum(vals.get("state", "manual") == "manual" for vals in vals_list),
            inverses_checked=len(inverses_wanted),
        )
        if any(model in self.pool for model in model_names):
            with _debug.perf("reload_schema", cr=self.env.cr, models=list(model_names)):
                reload_schema(self.env, model_names, model_names)

        return res

    def _check_inverses_exist(self, inverses: OrderedSet) -> None:
        found = {
            (field.model, field.name)
            for field in self.search(
                [
                    ("ttype", "=", "many2one"),
                    ("model", "in", [model_name for model_name, _ in inverses]),
                    ("name", "in", [name for _, name in inverses]),
                ]
            )
        }
        _debug.logic("inverses.checked", wanted=len(inverses), found=len(found))
        for model_name, name in inverses:
            if (model_name, name) not in found:
                _debug.logic(
                    "create.rejected",
                    model=model_name,
                    inverse=name,
                    reason="inverse_missing",
                )
                raise UserError(
                    _(
                        "Many2one %(field)s on model %(model)s does not exist!",
                        field=name,
                        model=model_name,
                    )
                )

    def _add_missing_group_xml_ids(self) -> None:
        groups = self.filtered(lambda field: field.state == "manual").groups
        if groups:
            _debug.lifecycle("group_xml_ids.added", groups=len(groups))
            groups.sudo()._add_missing_xml_ids()

    def _check_immutable_attributes(self, item: Self, vals: dict[str, Any]) -> None:
        if item.state != "manual":
            _debug.logic(
                "write.rejected",
                model=item.model,
                field=item.name,
                reason="base_field",
            )
            raise UserError(
                _(
                    "Properties of base fields cannot be altered in this manner! "
                    "Please modify them through Python code, "
                    "preferably through a custom addon!"
                )
            )
        if (
            vals.get("model_id", item.model_id.id) != item.model_id.id
            or vals.get("model", item.model) != item.model
        ):
            _debug.logic(
                "write.rejected",
                model=item.model,
                field=item.name,
                reason="model_change",
            )
            raise UserError(_("Changing the model of a field is forbidden!"))
        if vals.get("ttype", item.ttype) != item.ttype:
            _debug.logic(
                "write.rejected",
                model=item.model,
                field=item.name,
                reason="ttype_change",
            )
            raise UserError(
                _(
                    "Changing the type of a field is not yet supported. "
                    "Please drop it and create it again!"
                )
            )

    def _plan_write(self, vals: dict[str, Any]) -> tuple[Self, ColumnRename, set[str]]:
        renamed = self.browse()
        column_rename = None
        patched_models = set()

        for item in self:
            self._check_immutable_attributes(item, vals)
            model_cls = self.pool.get(item.model)
            field = getattr(model_cls, "_fields", {}).get(item.name)

            if vals.get("name", item.name) != item.name:
                renamed |= item
                if item.ttype not in ("one2many", "many2many", "binary"):
                    if column_rename:
                        _debug.logic(
                            "write.rejected",
                            field=item.name,
                            reason="multiple_renames",
                        )
                        raise UserError(_("Can only rename one field at a time!"))
                    if model_cls is None:
                        _debug.logic(
                            "write.rejected",
                            model=item.model,
                            field=item.name,
                            reason="model_not_in_registry",
                        )
                        raise UserError(
                            _(
                                "Cannot rename field \u201c%(field)s\u201d: its model "
                                "\u201c%(model)s\u201d is not in the registry.",
                                field=item.name,
                                model=item.model,
                            )
                        )
                    column_rename = (
                        model_cls._table,
                        item.name,
                        vals["name"],
                        item.index,
                        item.store,
                    )

            if model_cls is not None and field is not None:
                patched_models.add(model_cls._name)

        return renamed, column_rename, patched_models

    def _rename_xml_ids(self, old_names: dict[int, str]) -> None:
        entries = (
            self.env["ir.model.data"]
            .sudo()
            .search([("model", "=", self._name), ("res_id", "in", list(old_names))])
        )
        if not entries:
            _debug.logic("rename_xml_ids.skipped", fields=len(old_names))
            return
        by_id = {record.id: record for record in self}
        renamed = 0  # debuglog
        for entry in entries:
            record = by_id[entry.res_id]
            derived = field_xmlid(entry.module, record.model, old_names[entry.res_id])
            if entry.name != derived.partition(".")[2]:
                _debug.logic(
                    "rename_xml_ids.kept", xmlid=entry.id, reason="custom_name"
                )
                continue
            renamed += 1  # debuglog
            entry.name = field_xmlid(entry.module, record.model, record.name).partition(
                "."
            )[2]
        _debug.lifecycle("rename_xml_ids.done", entries=len(entries), renamed=renamed)

    def _rename_column(self, column_rename: ColumnRename) -> None:
        table, oldname, newname, index, stored = column_rename
        _debug.lifecycle(
            "rename_column", table=table, old=oldname, new=newname, stored=stored
        )
        if not stored:
            return
        self.env.flush_all()
        self.env.cr.execute(
            SQL(
                "ALTER TABLE %s RENAME COLUMN %s TO %s",
                SQL.identifier(table),
                SQL.identifier(oldname),
                SQL.identifier(newname),
            )
        )
        if index:
            _debug.lifecycle("rename_index", table=table, old=oldname, new=newname)
            self.env.cr.execute(
                SQL(
                    "ALTER INDEX IF EXISTS %s RENAME TO %s",
                    SQL.identifier(get_index_name(table, oldname)),
                    SQL.identifier(get_index_name(table, newname)),
                )
            )

    def write(self, vals: dict[str, Any]) -> bool:
        if not self or not vals:
            _debug.logic("write.skipped", count=len(self), fields=len(vals))
            return True

        for field_name in vals:
            if field_name not in self._fields:
                _debug.logic(
                    "write.rejected", field=field_name, reason="unknown_attribute"
                )
                raise ValueError(f"Invalid field {field_name!r} in {self._name!r}")

        translate_only = all(self._fields[field_name].translate for field_name in vals)
        translate_presence_changed = translate_only and any(
            bool(record[fname]) != bool(value)
            for fname, value in vals.items()
            for record in self
            if record.state == "manual"
        )

        if translate_only:
            renamed, column_rename, patched_models = self.browse(), None, set()
        else:
            renamed, column_rename, patched_models = self._plan_write(vals)
        _debug.lifecycle(
            "write",
            count=len(self),
            fields=list(vals),
            translate_only=translate_only,
            renamed=len(renamed),
            patched_models=sorted(patched_models),
        )

        vals = {
            key: value
            for key, value in vals.items()
            if key not in ("model_id", "model", "state")
        }

        _check_translate_value(vals)

        old_names = {record.id: record.name for record in renamed}

        if renamed:
            dependents = renamed._prepare_update(setup_models=False) - self
            _debug.pipeline(
                "write.rename_dependents_unlinked",
                renamed=len(renamed),
                dependents=len(dependents),
            )
            dependents.with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()

        res = super().write(vals)

        if column_rename:
            self._rename_column(column_rename)

        if renamed:
            renamed._rename_xml_ids(old_names)
            for record in renamed:
                if record.ttype == "binary":
                    record._rename_attachments_of_binary_field(old_names[record.id])

        if "groups" in vals:
            self._add_missing_group_xml_ids()

        if column_rename or patched_models:
            _debug.logic("write_reload", reason="column_rename_or_patched_models")
            reload_schema(self.env, OrderedSet(self.mapped("model")), patched_models)
        elif translate_presence_changed:
            _debug.logic("write_reload", reason="translate_presence_changed")
            reload_schema(self.env, OrderedSet(self.mapped("model")), ())
        elif translate_only:
            _debug.logic("write_reload", reason="translate_only_cache_clear")
            self.env.registry.clear_cache("stable")

        return res

    @api.depends("field_description", "model")
    def _compute_display_name(self) -> None:
        if self.env.context.get("hide_model"):
            _debug.logic("display_name.hide_model", count=len(self))
            for field in self:
                field.display_name = field.field_description
            return

        IrModel = self.env["ir.model"]
        with _debug.perf("display_name.prewarm", cr=self.env.cr, count=len(self)):
            IrModel._prewarm_names(list({field.model for field in self if field.model}))
        for field in self:
            model_string = IrModel._get(field.model).name
            field.display_name = f"{field.field_description} ({model_string})"

    def _prepare_field_vals(self, field: Any, model_id: int) -> dict[str, Any]:
        translate = TRANSLATE_KEY_BY_HANDLER.get(field.translate, "standard")
        return {
            "model_id": model_id,
            "model": field.model_name,
            "name": field.name,
            "field_description": field.string,
            "help": field.help or None,
            "ttype": field.type,
            "state": "manual" if field.manual else "base",
            "relation": field.comodel_name or None,
            "index": bool(field.index),
            "store": bool(field.store),
            "copied": bool(field.copy),
            "on_delete": field.ondelete if field.type == "many2one" else None,
            "related": field.related or None,
            "readonly": bool(field.readonly),
            "required": bool(field.required),
            "selectable": bool(field.search or field.store),
            "size": getattr(field, "size", None),
            "translate": translate,
            "company_dependent": bool(field.company_dependent),
            "relation_field": (
                field.inverse_name if field.type == "one2many" else None
            ),
            "relation_table": (field.relation if field.type == "many2many" else None),
            "column1": field.column1 if field.type == "many2many" else None,
            "column2": field.column2 if field.type == "many2many" else None,
            "currency_field": (
                field.currency_field if field.type == "monetary" else None
            ),
            "sanitize": field.sanitize if field.type == "html" else None,
            "sanitize_overridable": (
                field.sanitize_overridable if field.type == "html" else None
            ),
            "sanitize_tags": (field.sanitize_tags if field.type == "html" else None),
            "sanitize_attributes": (
                field.sanitize_attributes if field.type == "html" else None
            ),
            "sanitize_style": (field.sanitize_style if field.type == "html" else None),
            "sanitize_form": (field.sanitize_form if field.type == "html" else None),
            "strip_style": field.strip_style if field.type == "html" else None,
            "strip_classes": (field.strip_classes if field.type == "html" else None),
        }

    def _reflect_fields(self, model_names: list[str]) -> None:
        for model_name in model_names:
            model = self.env[model_name]
            by_label = {}
            for field in model._fields.values():
                if field.string in by_label:
                    other = by_label[field.string]
                    _debug.logic(
                        "reflect_fields.duplicate_label",
                        model=model_name,
                        field=field.name,
                        other=other.name,
                    )
                    _logger.warning(
                        "Two fields (%s, %s) of %s have the same label: %s. [Modules: %s and %s]",
                        field.name,
                        other.name,
                        model,
                        field.string,
                        field._module,
                        other._module,
                    )
                else:
                    by_label[field.string] = field

        ids_cache_generation = self._get_ids_by_name.__cache__.get_cache_generation(
            self
        )
        rows = []
        for model_name in model_names:
            model_id = self.env["ir.model"]._get_id(model_name)
            rows.extend(
                self._prepare_field_vals(field, model_id)
                for field in self.env[model_name]._fields.values()
            )
        if not rows:
            _debug.logic("reflect_fields.skipped", models=len(model_names))
            return
        cols = list(unique(["model", "name", *(key for row in rows for key in row)]))
        expected = [tuple(row.get(col) for col in cols) for row in rows]

        field_ids = {}
        existing = {}
        for row in select_en(self, ["id"] + cols, model_names):
            field_ids[row[1:3]] = row[0]
            existing[row[1:3]] = row[1:]

        rows = [row for row in expected if existing.get(row[:2]) != row]
        _debug.pipeline(
            "reflect_fields",
            models=len(model_names),
            expected=len(expected),
            existing=len(existing),
            changed=len(rows),
        )
        if rows:
            with _debug.perf("reflect_fields.upsert", cr=self.env.cr, rows=len(rows)):
                ids = upsert_en(self, cols, rows, ["model", "name"])
            for row, id_ in zip(rows, ids, strict=True):
                field_ids[row[:2]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # a lookup cached before this reflection would still answer with the old
        # field set; seed it with what the table holds now, as _reflect_models does
        ids_by_model: dict[str, dict[str, int]] = {name: {} for name in model_names}
        for (field_model, field_name), field_id in field_ids.items():
            ids_by_model[field_model][field_name] = field_id
        add_value = self._get_ids_by_name.__cache__.add_value
        for model_name, ids_by_name in ids_by_model.items():
            add_value(
                self,
                model_name,
                cache_value=ids_by_name,
                generation=ids_cache_generation,
            )

        module = self.env.context.get("module")
        if not module:
            _debug.logic("reflect_fields.no_xmlids", reason="no_module_in_context")
            return

        data_list = []
        for (field_model, field_name), field_id in field_ids.items():
            model = self.env[field_model]
            field = model._fields.get(field_name)
            if field and (
                module == model._original_module
                or module in field._modules
                or any(
                    field_name in self.env[parent]._fields
                    for parent, parent_module in model._inherit_module.items()
                    if module == parent_module
                )
            ):
                xml_id = field_xmlid(module, field_model, field_name)
                record = self.browse(field_id)
                data_list.append({"xml_id": xml_id, "record": record})
        _debug.pipeline("reflect_fields_xmlids", module=module, xmlids=len(data_list))
        self.env["ir.model.data"]._update_xmlids(data_list)

    @tools.ormcache(cache="stable")
    def _get_manual_field_data_by_model(self) -> dict[str, dict[str, Any]]:
        cr = self.env.cr
        cr.execute(
            """
            SELECT f.*,
                   f.field_description->>'en_US' AS field_description_en,
                   f.help->>'en_US' AS help_en,
                   g.group_count,
                   g.group_known,
                   g.group_xmlids
            FROM ir_model_fields f
            LEFT JOIN LATERAL (
                SELECT count(*) AS group_count,
                       count(x.xmlid) AS group_known,
                       string_agg(x.xmlid, ',' ORDER BY x.xmlid) AS group_xmlids
                FROM ir_model_fields_group_rel r
                LEFT JOIN LATERAL (
                    SELECT d.module || '.' || d.name AS xmlid
                    FROM ir_model_data d
                    WHERE d.model = 'res.groups' AND d.res_id = r.group_id
                    ORDER BY d.module, d.name
                    LIMIT 1
                ) x ON TRUE
                WHERE r.field_id = f.id
            ) g ON TRUE
            WHERE f.state = 'manual'
        """,
            prepare=False,
        )
        result: dict[str, dict[str, Any]] = defaultdict(dict)
        for row in cr.dictfetchall():
            row["field_description"] = row.pop("field_description_en")
            row["help"] = row.pop("help_en")
            result[row["model"]][row["name"]] = frozendict(row)
        _debug.perf.count(
            "manual_field_data_loaded",
            models=len(result),
            fields=sum(len(v) for v in result.values()),
        )
        return frozendict(result)

    def _get_manual_field_data(self, model_name: str) -> dict[str, Any]:
        return self._get_manual_field_data_by_model().get(model_name, {})

    def _is_field_ready(self, field_data: dict[str, Any]) -> bool:
        ready = self._is_field_ready_now(field_data)
        if _debug.logic.enabled and not ready:
            _debug.logic(
                "manual_field_deferred",
                model=field_data["model"],
                field=field_data["name"],
                ttype=field_data["ttype"],
                relation=field_data.get("relation"),
            )
        return ready

    def _is_field_ready_now(self, field_data: dict[str, Any]) -> bool:
        if self.pool.loaded:
            return True
        ttype = field_data["ttype"]
        if ttype in ("many2one", "many2many"):
            return field_data["relation"] in self.env
        if ttype == "one2many":
            comodel = field_data["relation"]
            return comodel in self.env and (
                field_data["relation_field"] in self.env[comodel]._fields
                or field_data["relation_field"] in self._get_manual_field_data(comodel)
            )
        if ttype == "monetary":
            return not field_data["currency_field"] or models.is_manual_name(
                field_data["currency_field"]
            )
        return True

    def _prepare_field_attrs(self, field_data: dict[str, Any]) -> dict[str, Any]:
        attrs = {
            "manual": True,
            "string": field_data["field_description"],
            "help": field_data["help"],
            "index": bool(field_data["index"]),
            "copy": bool(field_data["copied"]),
            "related": field_data["related"],
            "required": bool(field_data["required"]),
            "readonly": bool(field_data["readonly"]),
            "store": bool(field_data["store"]),
            "company_dependent": bool(field_data["company_dependent"]),
        }
        if group_count := field_data.get("group_count"):
            group_xmlids = field_data.get("group_xmlids")
            known = field_data.get("group_known") or 0
            attrs["groups"] = group_xmlids or NO_ACCESS
            if known != group_count:
                _debug.logic(
                    "field_attrs.groups_partial",
                    model=field_data["model"],
                    field=field_data["name"],
                    groups=group_count,
                    known=known,
                )
                _logger.error(
                    "Field %s.%s is restricted to %d group(s) but only %d of them "
                    "have an external id; the field is %s. Give every restricting "
                    "group an external id.",
                    field_data["model"],
                    field_data["name"],
                    group_count,
                    known,
                    "enforced against those only" if known else "hidden from everyone",
                )
        if field_data["ttype"] in ("char", "text", "html"):
            self._update_textual_field_attrs(field_data, attrs)
        elif field_data["ttype"] in ("selection", "reference"):
            attrs["selection"] = self.env[
                "ir.model.fields.selection"
            ]._get_selection_data(field_data["id"])
            if field_data["ttype"] == "selection":
                attrs["group_expand"] = field_data["group_expand"]
        elif field_data["ttype"] == "many2one":
            attrs["comodel_name"] = field_data["relation"]
            attrs["ondelete"] = field_data["on_delete"]
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
            attrs["group_expand"] = (
                "_read_group_expand_full" if field_data["group_expand"] else None
            )
        elif field_data["ttype"] == "one2many":
            attrs["comodel_name"] = field_data["relation"]
            attrs["inverse_name"] = field_data["relation_field"]
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
        elif field_data["ttype"] == "many2many":
            attrs["comodel_name"] = field_data["relation"]
            stored = (
                field_data["relation_table"],
                field_data["column1"],
                field_data["column2"],
            )
            if all(stored):
                attrs["relation"], attrs["column1"], attrs["column2"] = stored
            else:
                _debug.logic(
                    "field_attrs.m2m_names_derived",
                    model=field_data["model"],
                    field=field_data["name"],
                )
                derived = self._get_custom_many2many_names(
                    field_data["model"], field_data["relation"]
                )
                attrs["relation"], attrs["column1"], attrs["column2"] = (
                    value or fallback
                    for value, fallback in zip(stored, derived, strict=True)
                )
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
        elif field_data["ttype"] == "monetary":
            attrs["currency_field"] = field_data["currency_field"]
        if field_data["compute"]:
            _debug.logic(
                "field_attrs.compute_prepared",
                model=field_data["model"],
                field=field_data["name"],
            )
            attrs["compute"] = prepare_compute(
                field_data["compute"],
                field_data["depends"],
                f"{field_data['model']}.{field_data['name']}",
            )
        return attrs

    @staticmethod
    def _update_textual_field_attrs(
        field_data: dict[str, Any], attrs: dict[str, Any]
    ) -> None:
        attrs["translate"] = FIELD_TRANSLATE.get(field_data["translate"], True)
        if field_data["ttype"] == "char":
            attrs["size"] = field_data["size"] or None
        elif field_data["ttype"] == "html":
            attrs["sanitize"] = field_data["sanitize"]
            attrs["sanitize_overridable"] = field_data["sanitize_overridable"]
            attrs["sanitize_tags"] = field_data["sanitize_tags"]
            attrs["sanitize_attributes"] = field_data["sanitize_attributes"]
            attrs["sanitize_style"] = field_data["sanitize_style"]
            attrs["sanitize_form"] = field_data["sanitize_form"]
            attrs["strip_style"] = field_data["strip_style"]
            attrs["strip_classes"] = field_data["strip_classes"]

    @api.model
    def get_field_string(self, model_name: str) -> dict[str, str]:
        return {
            field_name: values["field_description"]
            for field_name, values in self._get_fields_cached(model_name).items()
        }

    @api.model
    def get_field_help(self, model_name: str) -> dict[str, str | None]:
        return {
            field_name: values["help"]
            for field_name, values in self._get_fields_cached(model_name).items()
        }

    @api.model
    def get_field_selection(
        self, model_name: str, field_name: str
    ) -> list[tuple[str, str]]:
        return (
            self._get_fields_cached(model_name).get(field_name, {}).get("selection", [])
        )

    @api.model
    @tools.ormcache("model_name", "self.env.lang", cache="stable")
    def _get_fields_cached(self, model_name: str) -> dict[str, dict[str, Any]]:
        fields_ = self.sudo().browse(self._get_ids_by_name(model_name).values())
        result = {
            field.name: {
                "id": field.id,
                "help": field.help,
                "field_description": field.field_description,
            }
            for field in fields_
        }
        for field in fields_.filtered(
            lambda field: field.ttype in ("selection", "reference")
        ):
            result[field.name]["selection"] = [
                (sel.value, sel.name) for sel in field.selection_ids
            ]
        _debug.perf.count(
            "fields_cached.cache_miss", model=model_name, fields=len(result)
        )
        return frozendict(result)
