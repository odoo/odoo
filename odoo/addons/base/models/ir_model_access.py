import logging
from typing import Any, Self

from psycopg.types.json import Json

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools import SQL, OrderedSet, sql
from odoo.tools.translate import _
from odoo.orm._typing import ValuesType

from .ir_model import (
    ACCESS_ERROR_GROUPS,
    ACCESS_ERROR_HEADER,
    ACCESS_ERROR_NOGROUP,
    ACCESS_ERROR_RESOLUTION,
)

_logger = logging.getLogger(__name__)


class IrModelConstraint(models.Model):
    """
    This model tracks PostgreSQL indexes, foreign keys and constraints
    used by Odoo models.
    """

    _name = "ir.model.constraint"
    _description = "Model Constraint"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Constraint",
        required=True,
        index=True,
        readonly=True,
        help="PostgreSQL constraint or foreign key name.",
    )
    definition = fields.Char(help="PostgreSQL constraint definition", readonly=True)
    message = fields.Char(
        help="Error message returned when the constraint is violated.",
        translate=True,
    )
    model = fields.Many2one(
        "ir.model", required=True, ondelete="cascade", index=True, readonly=True
    )
    module = fields.Many2one(
        "ir.module.module",
        required=True,
        index=True,
        ondelete="cascade",
        readonly=True,
    )
    type = fields.Char(
        string="Constraint Type",
        required=True,
        size=1,
        readonly=True,
        help="Type of the constraint: `f` for a foreign key, `u` for other constraints.",
    )

    _module_name_uniq = models.Constraint(
        "UNIQUE (name, module)",
        "Constraints with the same name are unique per module.",
    )

    def unlink(self) -> bool:
        self.check_access("unlink")
        ids_set = set(self.ids)
        for data in self.sorted(key="id", reverse=True):
            name = data.name
            if data.model.model in self.env:
                table = self.env[data.model.model]._table
            else:
                table = data.model.model.replace(".", "_")

            # double-check we are really going to delete all the owners of this schema element
            external_ids = {
                id_
                for [id_] in self.env.execute_query(
                    SQL(
                        """SELECT id from ir_model_constraint where name=%s""",
                        name,
                    )
                )
            }
            if external_ids - ids_set:
                # as installed modules have defined this element we must not delete it!
                continue

            typ = data.type
            if typ in ("f", "u"):
                # test if FK exists on this table
                # Since type='u' means any "other" constraint, to avoid issues we limit to
                # 'c' -> check, 'u' -> unique, 'x' -> exclude constraints, effective leaving
                # out 'p' -> primary key and 'f' -> foreign key, constraints.
                # For 'f', it could be on a related m2m table, in which case we ignore it.
                # See: https://www.postgresql.org/docs/9.5/catalog-pg-constraint.html
                hname = sql.make_identifier(name)
                if self.env.execute_query(
                    SQL(
                        """SELECT
                    FROM pg_constraint cs
                    JOIN pg_class cl
                    ON (cs.conrelid = cl.oid)
                    WHERE cs.contype = ANY(%s) AND cs.conname = %s AND cl.relname = %s
                    AND cl.relnamespace = current_schema::regnamespace
                    """,
                        ["c", "u", "x"] if typ == "u" else [typ],
                        hname,
                        table,
                    )
                ):
                    self.env.execute_query(
                        SQL(
                            "ALTER TABLE %s DROP CONSTRAINT %s",
                            SQL.identifier(table),
                            SQL.identifier(hname),
                        )
                    )
                    _logger.info("Dropped CONSTRAINT %s@%s", name, data.model.model)

            if typ == "i":
                hname = sql.make_identifier(name)
                # drop index if it exists
                self.env.execute_query(
                    SQL("DROP INDEX IF EXISTS %s", SQL.identifier(hname))
                )
                _logger.info("Dropped INDEX %s@%s", name, data.model.model)

        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=constraint.name + "_copy")
            for constraint, vals in zip(self, vals_list, strict=True)
        ]

    def _reflect_constraint(
        self,
        model: Any,
        conname: str,
        type: str,
        definition: str,
        module: str,
        message: str | None = None,
    ) -> Self | None:
        """Reflect the given constraint, and return its corresponding record
        if a record is created or modified; returns ``None`` otherwise.
        The reflection makes it possible to remove a constraint when its
        corresponding module is uninstalled. ``type`` is either 'f', 'i', or 'u'
        depending on the constraint being a foreign key or not.
        """
        if not module:
            # no need to save constraints for custom models as they're not part
            # of any module
            return None
        if type not in ("f", "u", "i"):
            raise ValueError(
                f"Invalid constraint type {type!r}: expected 'f', 'u', or 'i'."
            )
        rows = self.env.execute_query_dict(
            SQL(
                """SELECT c.id, type, definition, message->'en_US' as message
            FROM ir_model_constraint c, ir_module_module m
            WHERE c.module = m.id AND c.name = %s AND m.name = %s
            """,
                conname,
                module,
            )
        )
        if not rows:
            [[cons_id]] = self.env.execute_query(
                SQL(
                    """
                INSERT INTO ir_model_constraint
                    (name, create_date, write_date, create_uid, write_uid, module, model, type, definition, message)
                VALUES (%s,
                        now() AT TIME ZONE 'UTC',
                        now() AT TIME ZONE 'UTC',
                        %s, %s,
                        (SELECT id FROM ir_module_module WHERE name=%s),
                        (SELECT id FROM ir_model WHERE model=%s),
                        %s, %s, %s)
                RETURNING id
                """,
                    conname,
                    self.env.uid,
                    self.env.uid,
                    module,
                    model._name,
                    type,
                    definition,
                    Json({"en_US": message}),
                )
            )
            return self.browse(cons_id)
        [cons] = rows
        cons_id = cons.pop("id")
        if cons != {"type": type, "definition": definition, "message": message}:
            self.env.execute_query(
                SQL(
                    """
                UPDATE ir_model_constraint
                SET write_date=now() AT TIME ZONE 'UTC',
                    write_uid = %s, type = %s, definition = %s, message = %s
                WHERE id = %s""",
                    self.env.uid,
                    type,
                    definition,
                    Json({"en_US": message}),
                    cons_id,
                )
            )
            return self.browse(cons_id)
        return None

    def _reflect_constraints(self, model_names: list[str]) -> None:
        """Reflect the table objects of the given models."""
        for model_name in model_names:
            self._reflect_model(self.env[model_name])

    def _reflect_model(self, model: Any) -> None:
        """Reflect the _table_objects of the given model."""
        data_list = []
        for conname, cons in model._table_objects.items():
            module = cons._module
            if not conname or not module:
                _logger.warning("Missing module or constraint name for %s", cons)
                continue
            definition = cons.get_definition(model.pool)
            message = cons.message
            if not isinstance(message, str) or not message:
                message = None
            typ = "i" if isinstance(cons, models.Index) else "u"
            record = self._reflect_constraint(
                model, conname, typ, definition, module, message
            )
            xml_id = f"{module}.constraint_{conname}"
            if record:
                data_list.append({"xml_id": xml_id, "record": record})
            else:
                self.env["ir.model.data"]._load_xmlid(xml_id)
        if data_list:
            self.env["ir.model.data"]._update_xmlids(data_list)


class IrModelRelation(models.Model):
    """
    This model tracks PostgreSQL tables used to implement Odoo many2many
    relations.
    """

    _name = "ir.model.relation"
    _description = "Relation Model"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Relation Name",
        required=True,
        index=True,
        help="PostgreSQL table name implementing a many2many relation.",
    )
    model = fields.Many2one("ir.model", required=True, index=True, ondelete="cascade")
    module = fields.Many2one(
        "ir.module.module", required=True, index=True, ondelete="cascade"
    )
    write_date = fields.Datetime()
    create_date = fields.Datetime()

    def _module_data_uninstall(self) -> None:
        """
        Delete PostgreSQL many2many relations tracked by this model.
        """
        if not self.env.is_system():
            raise AccessError(
                _("Administrator access is required to uninstall a module")
            )

        ids_set = set(self.ids)
        to_drop = OrderedSet()
        for data in self.sorted(key="id", reverse=True):
            name = data.name

            # double-check we are really going to delete all the owners of this schema element
            self.env.cr.execute(
                """SELECT id from ir_model_relation where name = %s""", [name]
            )
            external_ids = {x[0] for x in self.env.cr.fetchall()}
            if not external_ids.issubset(ids_set):
                # as installed modules have defined this element we must not delete it!
                continue

            if sql.table_exists(self.env.cr, name):
                to_drop.add(name)

        self.unlink()

        # drop m2m relation tables
        for table in to_drop:
            self.env.cr.execute(SQL("DROP TABLE %s CASCADE", SQL.identifier(table)))
            _logger.info("Dropped table %s", table)

    def _reflect_relation(self, model: Any, table: str, module: str) -> None:
        """Reflect the table of a many2many field for the given model, to make
        it possible to delete it later when the module is uninstalled.
        """
        self.env.invalidate_all()
        cr = self.env.cr
        query = """ SELECT 1 FROM ir_model_relation r, ir_module_module m
                    WHERE r.module=m.id AND r.name=%s AND m.name=%s """
        cr.execute(query, (table, module))
        if not cr.rowcount:
            query = """ INSERT INTO ir_model_relation
                            (name, create_date, write_date, create_uid, write_uid, module, model)
                        VALUES (%s,
                                now() AT TIME ZONE 'UTC',
                                now() AT TIME ZONE 'UTC',
                                %s, %s,
                                (SELECT id FROM ir_module_module WHERE name=%s),
                                (SELECT id FROM ir_model WHERE model=%s)) """
            cr.execute(query, (table, self.env.uid, self.env.uid, module, model._name))


class IrModelAccess(models.Model):
    _name = "ir.model.access"
    _description = "Model Access"
    _order = "model_id,group_id,name,id"
    _allow_sudo_commands = False
    _PERM_COLUMNS = {
        "read": SQL("a.perm_read"),
        "write": SQL("a.perm_write"),
        "create": SQL("a.perm_create"),
        "unlink": SQL("a.perm_unlink"),
    }

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(
        default=True,
        help="If you uncheck the active field, it will disable the ACL without deleting it (if you delete a native ACL, it will be re-created when you reload the module).",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        index=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        "res.groups", string="Group", ondelete="restrict", index=True
    )
    perm_read = fields.Boolean(string="Read Access")
    perm_write = fields.Boolean(string="Write Access")
    perm_create = fields.Boolean(string="Create Access")
    perm_unlink = fields.Boolean(string="Delete Access")

    @api.model
    def group_names_with_access(self, model_name: str, access_mode: str) -> list[str]:
        """Return the names of visible groups which have been granted
         ``access_mode`` on the model ``model_name``.

        :rtype: list[str]
        """
        if access_mode not in ("read", "write", "create", "unlink"):
            raise ValueError(f"Invalid access mode: {access_mode!r}")
        lang = self.env.lang or "en_US"
        # Cast parameter to text so psycopg3 can infer the type for jsonb->> operators
        # without resorting to embedding the value as a raw SQL literal.
        perm_column = SQL.identifier(f"perm_{access_mode}")
        self.env.cr.execute(
            SQL(
                """
            SELECT COALESCE(c.name->>(%s::text), c.name->>'en_US'), COALESCE(g.name->>(%s::text), g.name->>'en_US')
              FROM ir_model_access a
              JOIN ir_model m ON (a.model_id = m.id)
              JOIN res_groups g ON (a.group_id = g.id)
         LEFT JOIN res_groups_privilege c ON (c.id = g.privilege_id)
             WHERE m.model = %s
               AND a.active = TRUE
               AND %s = TRUE
          ORDER BY c.name, g.name NULLS LAST
            """,
                lang,
                lang,
                model_name,
                perm_column,
            )
        )
        return [f"{x[0]}/{x[1]}" if x[0] else x[1] for x in self.env.cr.fetchall()]

    @api.model
    @tools.ormcache("model_name", "access_mode", cache="stable")
    def _get_access_groups(self, model_name: str, access_mode: str = "read") -> Any:
        """Return the group expression object that represents the users who
        have ``access_mode`` to the model ``model_name``.
        """
        if access_mode not in ("read", "write", "create", "unlink"):
            raise ValueError(f"Invalid access mode: {access_mode!r}")
        model = self.env["ir.model"]._get(model_name)
        accesses = self.sudo().search(
            [
                (f"perm_{access_mode}", "=", True),
                ("model_id", "=", model.id),
            ]
        )

        group_definitions = self.env["res.groups"]._get_group_definitions()
        if not accesses:
            return group_definitions.empty
        if not all(
            access.group_id for access in accesses
        ):  # there is some global access
            return group_definitions.universe
        return group_definitions.from_ids(accesses.group_id.ids)

    # The context parameter is useful when the method translates error messages.
    # But as the method raises an exception in that case,  the key 'lang' might
    # not be really necessary as a cache key, unless the `ormcache`
    # decorator catches the exception (it does not at the moment.)

    @tools.ormcache("self.env.uid", "mode")
    def _get_allowed_models(self, mode: str = "read") -> frozenset[str]:
        if mode not in ("read", "write", "create", "unlink"):
            raise ValueError(
                f"Invalid access mode {mode!r}: expected 'read', 'write', 'create', or 'unlink'."
            )

        group_ids = self.env.user._get_group_ids()
        self.flush_model()
        rows = self.env.execute_query(
            SQL(
                """
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
             WHERE %s
               AND a.active
               AND (
                    a.group_id IS NULL OR
                    a.group_id = ANY(%s)
                )
            GROUP BY m.model
        """,
                self._PERM_COLUMNS[mode],
                list(group_ids),
            )
        )

        return frozenset(v[0] for v in rows)

    @api.model
    def check(
        self, model: str, mode: str = "read", raise_exception: bool = True
    ) -> bool:
        if self.env.su:
            # User root have all accesses
            return True

        if not isinstance(model, str):
            raise TypeError(
                f"Model name must be a string, got {type(model).__name__}: {model!r}"
            )

        if model not in self.env:
            _logger.error("Missing model %s", model)

        has_access = model in self._get_allowed_models(mode)
        if not has_access and raise_exception:
            raise self._make_access_error(model, mode) from None
        return has_access

    def _make_access_error(self, model: str, mode: str) -> AccessError:
        """Return the exception corresponding to an access error."""
        _logger.info(
            "Access Denied by ACLs for operation: %s, uid: %s, model: %s",
            mode,
            self.env.uid,
            model,
        )

        operation_error = str(ACCESS_ERROR_HEADER[mode]) % {
            "document_kind": self.env["ir.model"]._get(model).name or model,
            "document_model": model,
        }

        groups = "\n".join(
            f"\t- {g}" for g in self.group_names_with_access(model, mode)
        )
        if groups:
            group_info = str(ACCESS_ERROR_GROUPS) % {"groups_list": groups}
        else:
            group_info = str(ACCESS_ERROR_NOGROUP)

        resolution_info = str(ACCESS_ERROR_RESOLUTION)

        return AccessError(
            operation_error + "\n\n" + group_info + "\n\n" + resolution_info
        )

    @api.model
    def call_cache_clearing_methods(self) -> None:
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")  # mainly _get_allowed_models

    #
    # Check rights on actions
    #
    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.call_cache_clearing_methods()
        for ima in vals_list:
            if (
                "group_id" in ima
                and not ima["group_id"]
                and any(
                    (
                        ima.get("perm_read"),
                        ima.get("perm_write"),
                        ima.get("perm_create"),
                        ima.get("perm_unlink"),
                    )
                )
            ):
                _logger.warning(
                    "Rule %s has no group, this is a deprecated feature. Every access-granting rule should specify a group.",
                    ima["name"],
                )
        return super().create(vals_list)

    def write(self, vals: dict[str, Any]) -> bool:
        self.call_cache_clearing_methods()
        return super().write(vals)

    def unlink(self) -> bool:
        self.call_cache_clearing_methods()
        return super().unlink()
