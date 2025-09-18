import contextlib
import gc
import logging
from ast import literal_eval
from collections import defaultdict
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.orm.registration import pop_field
from odoo.tools import SQL, OrderedSet, frozendict, sql, unique
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import FIELD_TRANSLATE, _
from odoo.orm._typing import ValuesType

from .ir_model import (
    MODULE_UNINSTALL_FLAG,
    field_xmlid,
    make_compute,
    mark_modified,
    select_en,
    upsert_en,
)

_logger = logging.getLogger(__name__)

# retrieve field types defined by the framework only (not extensions)
FIELD_TYPES = [(key, key) for key in sorted(fields.Field._by_type__)]


class IrModelFields(models.Model):
    _name = "ir.model.fields"
    _description = "Fields"
    _order = "name, id"
    _rec_name = "field_description"
    _allow_sudo_commands = False

    name = fields.Char(string="Field Name", default="x_", required=True, index=True)
    model = fields.Char(
        string="Model Name",
        required=True,
        index=True,
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
        "ir.model.fields",
        compute="_compute_relation_field_id",
        store=True,
        ondelete="cascade",
        string="Relation field",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        index=True,
        ondelete="cascade",
        help="The model this field belongs to",
    )
    field_description = fields.Char(
        string="Field Label", default="", required=True, translate=True
    )
    help = fields.Text(string="Field Help", translate=True)
    ttype = fields.Selection(selection=FIELD_TYPES, string="Field Type", required=True)
    selection = fields.Char(
        string="Selection Options (Deprecated)",
        compute="_compute_selection",
        inverse="_inverse_selection",
    )
    selection_ids = fields.One2many(
        "ir.model.fields.selection",
        "field_id",
        string="Selection Options",
        copy=True,
    )
    copied = fields.Boolean(
        string="Copied",
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
        "ir.model.fields",
        compute="_compute_related_field_id",
        store=True,
        string="Related Field",
        ondelete="cascade",
    )
    required = fields.Boolean()
    readonly = fields.Boolean()
    index = fields.Boolean(string="Indexed")
    translate = fields.Selection(
        [
            ("standard", "Translate as a whole"),
            ("html_translate", "Translate HTML terms"),
            ("xml_translate", "Translate XML terms"),
        ],
        string="Translatable",
        help="Whether values for this field can be translated (enables the translation mechanism for that field)",
    )
    company_dependent = fields.Boolean(
        string="Company Dependent",
        help="Whether values for this field is company dependent",
        readonly=True,
    )
    size = fields.Integer()
    state = fields.Selection(
        [("manual", "Custom Field"), ("base", "Base Field")],
        string="Type",
        default="manual",
        required=True,
        readonly=True,
        index=True,
    )
    on_delete = fields.Selection(
        [
            ("cascade", "Cascade"),
            ("set null", "Set NULL"),
            ("restrict", "Restrict"),
        ],
        string="On Delete",
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
        "res.groups", "ir_model_fields_group_rel", "field_id", "group_id"
    )  # CLEANME unimplemented field (empty table)
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
        compute="_in_modules",
        string="In Apps",
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
    # HTML sanitization reflection, useless for other kinds of fields
    sanitize = fields.Boolean(string="Sanitize HTML", default=True)
    sanitize_overridable = fields.Boolean(
        string="Sanitize HTML overridable", default=False
    )
    sanitize_tags = fields.Boolean(string="Sanitize HTML Tags", default=True)
    sanitize_attributes = fields.Boolean(
        string="Sanitize HTML Attributes", default=True
    )
    sanitize_style = fields.Boolean(string="Sanitize HTML Style", default=False)
    sanitize_form = fields.Boolean(string="Sanitize HTML Form", default=True)
    strip_style = fields.Boolean(string="Strip Style Attribute", default=False)
    strip_classes = fields.Boolean(string="Strip Class Attribute", default=False)

    @api.depends("relation", "relation_field")
    def _compute_relation_field_id(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.relation_field:
                rec.relation_field_id = self._get(rec.relation, rec.relation_field)
            else:
                rec.relation_field_id = False

    @api.depends("related")
    def _compute_related_field_id(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.related:
                rec.related_field_id = rec._related_field()
            else:
                rec.related_field_id = False

    @api.depends("selection_ids")
    def _compute_selection(self) -> None:
        for rec in self:
            if rec.ttype in ("selection", "reference"):
                rec.selection = str(
                    self.env["ir.model.fields.selection"]._get_selection(rec.id)
                )
            else:
                rec.selection = False

    def _inverse_selection(self) -> None:
        for rec in self:
            selection = literal_eval(rec.selection or "[]")
            self.env["ir.model.fields.selection"]._update_selection(
                rec.model, rec.name, selection
            )

    @api.depends("ttype", "related", "compute")
    def _compute_copied(self) -> None:
        for rec in self:
            rec.copied = (rec.ttype != "one2many") and not (rec.related or rec.compute)

    @api.depends()
    def _in_modules(self) -> None:
        installed_modules = self.env["ir.module.module"].search(
            [("state", "=", "installed")]
        )
        installed_names = set(installed_modules.mapped("name"))
        xml_ids = models.Model._get_external_ids(self)
        for field in self:
            module_names = {xml_id.split(".")[0] for xml_id in xml_ids[field.id]}
            field.modules = ", ".join(sorted(installed_names & module_names))

    @api.constrains("domain")
    def _check_domain(self) -> None:
        for field in self:
            try:
                safe_eval(field.domain or "[]")
            except (ValueError, SyntaxError) as e:
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
                models.check_pg_name(field.name)
            except ValidationError as e:
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

    def _related_field(self) -> Self:
        """Return the ``ir.model.fields`` record corresponding to ``self.related``."""
        names = self.related.split(".")
        last = len(names) - 1
        model_name = self.model or self.model_id.model
        for index, name in enumerate(names):
            field = self._get(model_name, name)
            if not field:
                raise UserError(
                    _(
                        'Unknown field name "%(field_name)s" in related field "%(related_field)s"',
                        field_name=name,
                        related_field=self.related,
                    )
                )
            model_name = field.relation
            if index < last and not field.relation:
                raise UserError(
                    _(
                        'Non-relational field name "%(field_name)s" in related field "%(related_field)s"',
                        field_name=name,
                        related_field=self.related,
                    )
                )
        return field

    @api.constrains("related")
    def _check_related(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.related:
                field = rec._related_field()
                if field.ttype != rec.ttype:
                    raise ValidationError(
                        _(
                            'Related field "%(related_field)s" does not have type "%(type)s"',
                            related_field=rec.related,
                            type=rec.ttype,
                        )
                    )
                if field.relation != rec.relation:
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
                field = self._related_field()
            except UserError as e:
                return {"warning": {"title": _("Warning"), "message": e}}
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
                raise ValidationError(
                    _("Unknown model name '%s' in Related Model", rec.relation)
                )

    @api.constrains("depends")
    def _check_depends(self) -> None:
        """Check whether all fields in dependencies are valid."""
        for record in self:
            if not record.depends:
                continue
            for seq in record.depends.split(","):
                if not seq.strip():
                    raise UserError(
                        _("Empty dependency in \u201c%s\u201d", record.depends)
                    )
                model = self.env[record.model]
                names = seq.strip().split(".")
                last = len(names) - 1
                for index, name in enumerate(names):
                    if name == "id":
                        raise UserError(_("Compute method cannot depend on field 'id'"))
                    field = model._fields.get(name)
                    if field is None:
                        raise UserError(
                            _(
                                "Unknown field \u201c%(field)s\u201d in dependency \u201c%(dependency)s\u201d",
                                field=name,
                                dependency=seq.strip(),
                            )
                        )
                    if index < last and not field.relational:
                        raise UserError(
                            _(
                                "Non-relational field \u201c%(field)s\u201d in dependency \u201c%(dependency)s\u201d",
                                field=name,
                                dependency=seq.strip(),
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
                models.check_pg_name(rec.relation_table)

    @api.constrains("currency_field")
    def _check_currency_field(self) -> None:
        for rec in self:
            if rec.state == "manual" and rec.ttype == "monetary":
                if not rec.currency_field:
                    currency_field = self._get(rec.model, "currency_id") or self._get(
                        rec.model, "x_currency_id"
                    )
                    if not currency_field:
                        raise ValidationError(
                            _(
                                "Currency field is empty and there is no fallback field in the model"
                            )
                        )
                else:
                    currency_field = self._get(rec.model, rec.currency_field)
                    if not currency_field:
                        raise ValidationError(
                            _(
                                "Unknown field specified \u201c%s\u201d in currency_field",
                                rec.currency_field,
                            )
                        )

                if currency_field.ttype != "many2one":
                    raise ValidationError(
                        _("Currency field does not have type many2one")
                    )
                if currency_field.relation != "res.currency":
                    raise ValidationError(
                        _("Currency field should have a res.currency relation")
                    )

    @api.model
    def _custom_many2many_names(
        self, model_name: str, comodel_name: str
    ) -> tuple[str, str, str]:
        """Return default names for the table and columns of a custom many2many field."""
        rel1 = self.env[model_name]._table
        rel2 = self.env[comodel_name]._table
        s1, s2 = sorted([rel1, rel2])
        table = f"x_{s1}_{s2}_rel"
        if rel1 == rel2:
            return (table, "id1", "id2")
        else:
            return (table, f"{rel1}_id", f"{rel2}_id")

    @api.onchange("ttype", "model_id", "relation")
    def _onchange_ttype(self) -> None:
        if self.ttype == "many2many" and self.model_id and self.relation:
            if self.relation not in self.env:
                return
            names = self._custom_many2many_names(self.model_id.model, self.relation)
            self.relation_table, self.column1, self.column2 = names
        else:
            self.relation_table = False
            self.column1 = False
            self.column2 = False

    @api.onchange("relation_table")
    def _onchange_relation_table(self) -> dict[str, Any] | None:
        if self.relation_table:
            # check whether other fields use the same table
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
                        # other is a candidate inverse field
                        self.column1 = other.column2
                        self.column2 = other.column1
                        return None
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
                raise ValidationError(
                    _(
                        "The m2o field %s is required but declares its ondelete policy "
                        "as being 'set null'. Only 'restrict' and 'cascade' make sense.",
                        rec.name,
                    )
                )

    def _get(self, model_name: str, name: str) -> Self:
        """Return the (sudoed) `ir.model.fields` record with the given model and name.
        The result may be an empty recordset if the model is not found.
        """
        field_id = model_name and name and self._get_ids(model_name).get(name)
        return self.sudo().browse(field_id)

    @tools.ormcache("model_name", cache="stable")
    def _get_ids(self, model_name: str) -> dict[str, int]:
        cr = self.env.cr
        cr.execute("SELECT name, id FROM ir_model_fields WHERE model=%s", [model_name])
        return dict(cr.fetchall())

    def _drop_column(self) -> bool:
        tables_to_drop = set()

        for field in self:
            if field.name in models.MAGIC_COLUMNS:
                continue
            model = self.env.get(field.model)
            is_model = model is not None
            if field.store:
                # TODO: refactor this convoluted unlink/drop logic
                if (
                    is_model
                    and sql.column_exists(self.env.cr, model._table, field.name)
                    and sql.table_kind(self.env.cr, model._table)
                    == sql.TableKind.Regular
                ):
                    self.env.cr.execute(
                        SQL(
                            "ALTER TABLE %s DROP COLUMN %s CASCADE",
                            SQL.identifier(model._table),
                            SQL.identifier(field.name),
                        )
                    )
                if field.state == "manual" and field.ttype == "many2many":
                    rel_name = field.relation_table or (
                        is_model and model._fields[field.name].relation
                    )
                    if rel_name:
                        tables_to_drop.add(rel_name)
            if field.state == "manual" and is_model:
                model_cls = self.env.registry[model._name]
                pop_field(model_cls, field.name)

        if tables_to_drop:
            # drop the relation tables that are not used by other fields
            self.env.cr.execute(
                """SELECT relation_table FROM ir_model_fields
                                WHERE relation_table = ANY(%s) AND id != ALL(%s)""",
                (list(tables_to_drop), list(self.ids)),
            )
            tables_to_keep = {row[0] for row in self.env.cr.fetchall()}
            for rel_name in tables_to_drop - tables_to_keep:
                self.env.cr.execute(SQL("DROP TABLE %s", SQL.identifier(rel_name)))

        return True

    def _prepare_update(self) -> Self:
        """Check whether the fields in ``self`` may be modified or removed.
        This method prevents the modification/deletion of many2one fields
        that have an inverse one2many, for instance.
        """
        uninstalling = self.env.context.get(MODULE_UNINSTALL_FLAG)
        if not uninstalling and any(record.state != "manual" for record in self):
            raise UserError(
                _("This column contains module data and cannot be removed!")
            )

        records = self  # all the records to delete
        fields_ = OrderedSet()  # all the fields corresponding to 'records'
        failed_dependencies = []  # list of broken (field, dependent_field)

        for record in self:
            model = self.env.get(record.model)
            if model is None:
                continue
            field = model._fields.get(record.name)
            if field is None:
                continue
            fields_.add(field)
            for dep in self.pool.get_dependent_fields(field):
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

        self = records

        if failed_dependencies:
            if not uninstalling:
                field, dep = failed_dependencies[0]
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

        records = self.filtered(lambda record: record.state == "manual")
        if not records:
            return self

        # remove pending write of this field
        # DLE P16: if there are pending updates of the field we currently try to unlink, pop them out from the cache
        # test `test_unlink_with_dependent`
        for record in records:
            model = self.env.get(record.model)
            field = model and model._fields.get(record.name)
            if field:
                self.env._core.pop_dirty(field)
        # remove fields from registry, and check that views are not broken
        fields = [
            pop_field(self.env.registry[record.model], record.name)
            for record in records
        ]
        domain = Domain.OR([("arch_db", "like", record.name)] for record in records)
        views = self.env["ir.ui.view"].search(domain)
        try:
            for view in views:
                view._check_xml()
        except Exception:
            if not uninstalling:
                raise UserError(
                    _(
                        "Cannot rename/delete fields that are still present in views:\nFields: %(fields)s\nView: %(view)s",
                        fields=fields,
                        view=view.name,
                    )
                )
            # uninstall mode
            _logger.warning(
                "The following fields were force-deleted to prevent a registry crash %s the following view might be broken %s",
                ", ".join(str(f) for f in fields),
                view.name,
            )
        finally:
            if not uninstalling:
                # the registry has been modified, restore it
                self.pool._setup_models__(self.env.cr)

        return self

    def unlink(self) -> bool:
        if not self:
            return True

        # prevent screwing up fields that depend on these fields
        self = self._prepare_update()

        # determine registry fields corresponding to self
        fields = OrderedSet()
        for record in self:
            with contextlib.suppress(KeyError):
                fields.add(self.pool[record.model]._fields[record.name])

        # clean the registry from the fields to remove
        self.pool.registry_invalidated = True
        self.pool._discard_fields(fields)

        # discard the removed fields from fields to compute
        for field in fields:
            self.env._core.discard_field(field)

        model_names = self.mapped("model")
        self._drop_column()
        res = super().unlink()

        # The field we just deleted might be inherited, and the registry is
        # inconsistent in this case; therefore we reload the registry.
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this re-initializes models in registry
            self.env.flush_all()
            self.pool._setup_models__(self.env.cr, model_names)
            # update database schema of model and its descendant models
            models = self.pool.descendants(model_names, "_inherits")
            self.pool.init_models(
                self.env.cr,
                models,
                dict(self.env.context, update_custom_fields=True),
            )

        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        IrModel = self.env["ir.model"]
        for vals in vals_list:
            if vals.get("translate") and not isinstance(vals["translate"], str):
                _logger.warning(
                    "Deprecated since Odoo 19, ir.model.fields.translate becomes Selection, the value should be a string"
                )
                vals["translate"] = (
                    "html_translate" if vals.get("ttype") == "html" else "standard"
                )
            if "model_id" in vals:
                vals["model"] = IrModel.browse(vals["model_id"]).model

        # Validate before creating records to fail fast
        for vals in vals_list:
            if vals.get("state", "manual") == "manual":
                relation = vals.get("relation")
                if relation and not IrModel._get_id(relation):
                    raise UserError(_("Model %s does not exist!", vals["relation"]))

                if (
                    vals.get("ttype") == "one2many"
                    and vals.get("store", True)
                    and not vals.get("related")
                    and vals.get("relation_field")
                    and not self.search_count(
                        [
                            ("ttype", "=", "many2one"),
                            ("model", "=", vals["relation"]),
                            ("name", "=", vals["relation_field"]),
                        ]
                    )
                ):
                    raise UserError(
                        _(
                            "Many2one %(field)s on model %(model)s does not exist!",
                            field=vals["relation_field"],
                            model=vals["relation"],
                        )
                    )

        # for self._get_ids() in _update_selection()
        self.env.registry.clear_cache("stable")

        res = super().create(vals_list)
        models = OrderedSet(res.mapped("model"))

        if any(model in self.pool for model in models):
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool._setup_models__(self.env.cr, models)
            # update database schema of models and their descendants
            models = self.pool.descendants(models, "_inherits")
            self.pool.init_models(
                self.env.cr,
                models,
                dict(self.env.context, update_custom_fields=True),
            )

        return res

    def write(self, vals: dict[str, Any]) -> bool:
        if not self:
            return True

        # if set, *one* column can be renamed here
        column_rename = None

        # names of the models to patch
        patched_models = set()
        translate_only = all(self._fields[field_name].translate for field_name in vals)
        if vals and self and not translate_only:
            for item in self:
                if item.state != "manual":
                    raise UserError(
                        _(
                            "Properties of base fields cannot be altered in this manner! "
                            "Please modify them through Python code, "
                            "preferably through a custom addon!"
                        )
                    )

                if vals.get("model_id", item.model_id.id) != item.model_id.id:
                    raise UserError(_("Changing the model of a field is forbidden!"))

                if vals.get("ttype", item.ttype) != item.ttype:
                    raise UserError(
                        _(
                            "Changing the type of a field is not yet supported. Please drop it and create it again!"
                        )
                    )

                obj = self.pool.get(item.model)
                field = getattr(obj, "_fields", {}).get(item.name)

                if vals.get("name", item.name) != item.name:
                    # We need to rename the field
                    item._prepare_update()
                    if item.ttype in ("one2many", "many2many", "binary"):
                        # those field names are not explicit in the database!
                        pass
                    else:
                        if column_rename:
                            raise UserError(_("Can only rename one field at a time!"))
                        column_rename = (
                            obj._table,
                            item.name,
                            vals["name"],
                            item.index,
                            item.store,
                        )

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj is not None and field is not None:
                    patched_models.add(obj._name)

        # These shall never be written (modified)
        for column_name in ("model_id", "model", "state"):
            vals.pop(column_name, None)

        if vals.get("translate") and not isinstance(vals["translate"], str):
            _logger.warning(
                "Deprecated since Odoo 19, ir.model.fields.translate becomes Selection, the value should be a string"
            )
            vals["translate"] = (
                "html_translate" if vals.get("ttype") == "html" else "standard"
            )

        if column_rename and all(rec.state == "manual" for rec in self):
            # renaming a studio field, remove inherits fields
            # we need to set the uninstall flag to allow removing them
            (self._prepare_update() - self).with_context(
                **{MODULE_UNINSTALL_FLAG: True}
            ).unlink()

        res = super().write(vals)

        self.env.flush_all()

        if column_rename:
            # rename column in database, and its corresponding index if present
            table, oldname, newname, index, stored = column_rename
            if stored:
                self.env.cr.execute(
                    SQL(
                        "ALTER TABLE %s RENAME COLUMN %s TO %s",
                        SQL.identifier(table),
                        SQL.identifier(oldname),
                        SQL.identifier(newname),
                    )
                )
                if index:
                    self.env.cr.execute(
                        SQL(
                            "ALTER INDEX %s RENAME TO %s",
                            SQL.identifier(f"{table}_{oldname}_index"),
                            SQL.identifier(f"{table}_{newname}_index"),
                        )
                    )

        if column_rename or patched_models or translate_only:
            # setup models, this will reload all manual fields in registry
            self.env.flush_all()
            model_names = OrderedSet(self.mapped("model"))
            self.pool._setup_models__(self.env.cr, model_names)

        if patched_models:
            # update the database schema of the models to patch
            models = self.pool.descendants(patched_models, "_inherits")
            self.pool.init_models(
                self.env.cr,
                models,
                dict(self.env.context, update_custom_fields=True),
            )

        return res

    @api.depends("field_description", "model")
    def _compute_display_name(self) -> None:
        IrModel = self.env["ir.model"]
        if not self.env.context.get("hide_model"):
            # Pre-warm ormcache: single query for all distinct model names
            # instead of one query per unique model on cache miss.
            model_names = list({f.model for f in self if f.model})
            if model_names:
                add_value = IrModel._get_id.__cache__.add_value
                for model_name, model_id in self.env.execute_query(
                    SQL(
                        "SELECT model, id FROM ir_model WHERE model = ANY(%s)",
                        model_names,
                    )
                ):
                    add_value(IrModel, model_name, cache_value=model_id)
        for field in self:
            if self.env.context.get("hide_model"):
                field.display_name = field.field_description
                continue
            model_string = IrModel._get(field.model).name
            field.display_name = f"{field.field_description} ({model_string})"

    def _reflect_field_params(self, field: Any, model_id: int) -> dict[str, Any]:
        """Return the values to write to the database for the given field."""
        translate = next(
            (k for k, v in FIELD_TRANSLATE.items() if v == field.translate),
            "standard",
        )
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
            # html sanitization attributes (useless for other fields)
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
        """Reflect the fields of the given models."""
        # Free accumulated garbage from previous module loads before the
        # memory-intensive field reflection phase.
        gc.collect()

        for model_name in model_names:
            model = self.env[model_name]
            by_label = {}
            for field in model._fields.values():
                if field.string in by_label:
                    other = by_label[field.string]
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

        # determine expected and existing rows
        rows = []
        for model_name in model_names:
            model_id = self.env["ir.model"]._get_id(model_name)
            rows.extend(
                self._reflect_field_params(field, model_id)
                for field in self.env[model_name]._fields.values()
            )
        if not rows:
            return
        cols = list(unique(["model", "name"] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]

        field_ids = {}
        existing = {}
        for row in select_en(self, ["id"] + cols, model_names):
            field_ids[row[1:3]] = row[0]
            existing[row[1:3]] = row[1:]

        # create or update rows
        rows = [row for row in expected if existing.get(row[:2]) != row]
        if rows:
            ids = upsert_en(self, cols, rows, ["model", "name"])
            for row, id_ in zip(rows, ids, strict=True):
                field_ids[row[:2]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # update their XML id
        module = self.env.context.get("module")
        if not module:
            return

        data_list = []
        for (field_model, field_name), field_id in field_ids.items():
            model = self.env[field_model]
            field = model._fields.get(field_name)
            if field and (
                module == model._original_module
                or module in field._modules
                or any(
                    # module introduced field on model by inheritance
                    field_name in self.env[parent]._fields
                    for parent, parent_module in model._inherit_module.items()
                    if module == parent_module
                )
            ):
                xml_id = field_xmlid(module, field_model, field_name)
                record = self.browse(field_id)
                data_list.append({"xml_id": xml_id, "record": record})
        self.env["ir.model.data"]._update_xmlids(data_list)

    @tools.ormcache(cache="stable")
    def _all_manual_field_data(self) -> dict[str, dict[str, Any]]:
        cr = self.env.cr
        # we cannot use self._fields to determine translated fields, as it has not been set up yet
        cr.execute("""
            SELECT *, field_description->>'en_US' AS field_description, help->>'en_US' AS help
            FROM ir_model_fields
            WHERE state = 'manual'
        """)
        result = defaultdict(dict)
        for row in cr.dictfetchall():
            result[row["model"]][row["name"]] = row
        return result

    def _get_manual_field_data(self, model_name: str) -> dict[str, Any]:
        """Return the given model's manual field data."""
        return self._all_manual_field_data().get(model_name, {})

    def _instantiate_attrs(self, field_data: dict[str, Any]) -> dict[str, Any] | None:
        """Return the parameters for a field instance for ``field_data``."""
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
        if field_data["ttype"] in ("char", "text", "html"):
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
        elif field_data["ttype"] in ("selection", "reference"):
            attrs["selection"] = self.env[
                "ir.model.fields.selection"
            ]._get_selection_data(field_data["id"])
            if field_data["ttype"] == "selection":
                attrs["group_expand"] = field_data["group_expand"]
        elif field_data["ttype"] == "many2one":
            if not self.pool.loaded and field_data["relation"] not in self.env:
                return None
            attrs["comodel_name"] = field_data["relation"]
            attrs["ondelete"] = field_data["on_delete"]
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
            attrs["group_expand"] = (
                "_read_group_expand_full" if field_data["group_expand"] else None
            )
        elif field_data["ttype"] == "one2many":
            if not self.pool.loaded and not (
                field_data["relation"] in self.env
                and (
                    field_data["relation_field"]
                    in self.env[field_data["relation"]]._fields
                    or field_data["relation_field"]
                    in self._get_manual_field_data(field_data["relation"])
                )
            ):
                return None
            attrs["comodel_name"] = field_data["relation"]
            attrs["inverse_name"] = field_data["relation_field"]
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
        elif field_data["ttype"] == "many2many":
            if not self.pool.loaded and field_data["relation"] not in self.env:
                return None
            attrs["comodel_name"] = field_data["relation"]
            rel, col1, col2 = self._custom_many2many_names(
                field_data["model"], field_data["relation"]
            )
            attrs["relation"] = field_data["relation_table"] or rel
            attrs["column1"] = field_data["column1"] or col1
            attrs["column2"] = field_data["column2"] or col2
            attrs["domain"] = safe_eval(field_data["domain"] or "[]")
        elif field_data["ttype"] == "monetary":
            # be sure that custom monetary fields are always instantiated
            if (
                not self.pool.loaded
                and field_data["currency_field"]
                and not self._is_manual_name(field_data["currency_field"])
            ):
                return None
            attrs["currency_field"] = field_data["currency_field"]
        # add compute function if given
        if field_data["compute"]:
            attrs["compute"] = make_compute(
                field_data["compute"], field_data["depends"]
            )
        return attrs

    @api.model
    def _is_manual_name(self, name: str) -> bool:
        return name.startswith("x_")

    @api.model
    def get_field_string(self, model_name: str) -> dict[str, str]:
        """Return the translation of fields strings in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' strings as a dictionary `{field_name: field_string}`
        """
        return {
            field_name: values["field_description"]
            for field_name, values in self._get_fields_cached(model_name).items()
        }

    @api.model
    def get_field_help(self, model_name: str) -> dict[str, str | None]:
        """Return the translation of fields help in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' help as a dictionary `{field_name: field_help}`
        """
        return {
            field_name: values["help"]
            for field_name, values in self._get_fields_cached(model_name).items()
        }

    @api.model
    def get_field_selection(
        self, model_name: str, field_name: str
    ) -> list[tuple[str, str]]:
        """Return the translation of a field's selection in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of the field's model
        :param field_name: the name of the field
        :return: the fields' selection as a list
        """
        return (
            self._get_fields_cached(model_name).get(field_name, {}).get("selection", [])
        )

    @api.model
    @tools.ormcache("model_name", "self.env.lang", cache="stable")
    def _get_fields_cached(self, model_name: str) -> dict[str, dict[str, Any]]:
        """Return the translated information of all model field's in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of the field's model
        :return: {field_name: {id, help, field_description, [selection]}}
        """
        fields = self.sudo().browse(self._get_ids(model_name).values())
        result = {
            field.name: {
                "id": field.id,
                "help": field.help,
                "field_description": field.field_description,
            }
            for field in fields
        }
        for field in fields.filtered(
            lambda field: field.ttype in ("selection", "reference")
        ):
            result[field.name]["selection"] = [
                (sel.value, sel.name) for sel in field.selection_ids
            ]
        return frozendict(result)
