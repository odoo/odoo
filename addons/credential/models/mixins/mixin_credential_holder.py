import json
import logging
from uuid import uuid4

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

NATIVE_CREDENTIAL_FIELDS = frozenset({"api_key", "api_secret", "username", "password"})


class MixinCredentialHolder(models.AbstractModel):
    """A record whose own secret fields are doors onto one credential.

    The concrete model declares the Many2one named by `_credential_holder_field`,
    maps each door to a vault key in `_CREDENTIAL_FIELDS`, and declares every door
    as ``fields.Char(compute="_compute_credential_doors",
    inverse="_inverse_credential_doors")``, with ``copy=True`` when a copy of the
    record should carry the secret. A key in `NATIVE_CREDENTIAL_FIELDS`
    lands in that credential field; any other key is a member of
    `credential_data`.

    Secrets written through `create` and `write` are routed out of the values
    before the ORM sees them. The ORM protects every field computed by one
    method during a write, so an inverse shared by all doors would read the
    doors not being written as empty and clear them.
    """

    _name = "mixin.credential.holder"
    _description = "Credential Holder"

    _credential_holder_field = "credential_id"
    _credential_purpose = "credential:holder"
    _CREDENTIAL_FIELDS: dict[str, str] = {}

    def _credential_field_map(self) -> dict[str, str]:
        """Every inheriting module's doors, merged in load order.

        `_CREDENTIAL_FIELDS` is a plain class attribute, so reading it returns
        only the last-loaded module's mapping. The merge is cached per MRO: the
        registry keeps a model's class and swaps its bases as modules load.
        """
        model_class = type(self)
        mro = model_class.__mro__
        cached = vars(model_class).get("_credential_field_map_merged")
        if cached is None or cached[0] is not mro:
            mapping: dict[str, str] = {}
            for cls in reversed(mro):
                mapping.update(vars(cls).get("_CREDENTIAL_FIELDS") or {})
            cached = model_class._credential_field_map_merged = (mro, mapping)
        return cached[1]

    def _credential_holder_name(self) -> str:
        """Unique per record: credentials are unique on (company_id, name)."""
        self.check_singleton()
        return f"{self.display_name or self._description} [#{self.id}]"

    def _credential_company_id(self):
        self.check_singleton()
        return self.company_id.id if "company_id" in self._fields else False

    def _pop_door_values(self, vals: dict) -> dict:
        field_map = self._credential_field_map()
        return {
            field_map[door]: self._fields[door].convert_to_cache(vals.pop(door), self)
            or False
            for door in list(vals)
            if door in field_map
        }

    @api.model_create_multi
    def create(self, vals_list):
        holder = self._credential_holder_field
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            secrets = {k: v for k, v in self._pop_door_values(vals).items() if v}
            if secrets:
                vals[holder] = self._create_holding_credential(
                    f"{self._description} [{uuid4().hex[:12]}]", False, secrets
                ).id
        records = super().create(vals_list)
        for record in records.sudo():
            if record[holder]:
                record[holder].write(
                    {
                        "name": record._credential_holder_name(),
                        "company_id": record._credential_company_id(),
                    }
                )
        return records

    def write(self, vals):
        vals = dict(vals)
        field_map = self._credential_field_map()
        written = [door for door in vals if door in field_map]
        secrets = self._pop_door_values(vals)
        if secrets:
            written_fields = [self._fields[name] for name in vals]
            with self.env.protecting(written_fields, self):
                for record in self:
                    record._set_held_secrets(secrets)
                self.invalidate_recordset(written)
                self.modified(written)
        result = super().write(vals)
        if secrets:
            self._check_fields(written)
        return result

    @api.depends(lambda self: (self._credential_holder_field,))
    def _compute_credential_doors(self):
        field_map = self._credential_field_map()
        for record in self:
            secrets = record._get_held_secrets()
            for door, key in field_map.items():
                record[door] = secrets.get(key) or False

    def _inverse_credential_doors(self):
        """Doors are routed in `create` and `write`; see the class docstring."""

    def _get_held_secrets(self) -> dict:
        self.check_singleton()
        credential = self.sudo()[self._credential_holder_field]
        if not credential:
            return {}
        return credential._use_secret_payload(self._credential_purpose)

    def _get_held_secret(self, key: str):
        return self._get_held_secrets().get(key) or False

    def _post_held_oauth2_refresh_grant(
        self, token_url, refresh_key, client_auth, *, purpose, **options
    ):
        """Spend the refresh token held under `refresh_key`, the row locked first.

        Returns the token endpoint's response, or None when no refresh token is
        held. Storing what it returns is the caller's, inside this transaction.
        """
        self.check_singleton()
        credential = self.sudo()[self._credential_holder_field]
        if not credential:
            return None
        credential._lock_for_oauth2_refresh()
        refresh_token = credential._use_secret_payload(f"{purpose}:oauth2_refresh").get(
            refresh_key
        )
        if not refresh_token:
            return None
        return credential._post_oauth2_refresh_grant(
            token_url, refresh_token, client_auth, purpose=purpose, **options
        )

    @api.model
    def _create_holding_credential(self, name, company_id, secrets):
        native = {k: v for k, v in secrets.items() if k in NATIVE_CREDENTIAL_FIELDS}
        extra = {k: v for k, v in secrets.items() if k not in native}
        return (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": name,
                    "category_id": self.env.ref(
                        "credential.credential_category_custom"
                    ).id,
                    "company_id": company_id,
                    **native,
                    **({"credential_data": json.dumps(extra)} if extra else {}),
                }
            )
        )

    def _set_held_secrets(self, secrets: dict) -> None:
        """Write some of this record's secrets, keeping the others.

        A false value removes that secret. A credential left holding nothing is
        unlinked, and a record holding no secret holds no credential.
        """
        self.check_singleton()
        credential = self.sudo()[self._credential_holder_field]
        if not credential:
            if not any(secrets.values()):
                return
            credential = self._create_holding_credential(
                self._credential_holder_name(), self._credential_company_id(), {}
            )
            super(MixinCredentialHolder, self.sudo()).write(
                {self._credential_holder_field: credential.id}
            )

        native = {
            key: value or False
            for key, value in secrets.items()
            if key in NATIVE_CREDENTIAL_FIELDS
        }
        extra = {key: value for key, value in secrets.items() if key not in native}
        if native:
            credential.write(native)
        if extra:
            data = (
                {
                    key: value
                    for key, value in credential._use_secret_payload(
                        self._credential_purpose
                    ).items()
                    if key not in credential._JSON_ACCESSOR_FIELDS
                }
                if credential.storage_method == "json"
                else {}
            )
            for key, value in extra.items():
                if value:
                    data[key] = value
                else:
                    data.pop(key, None)
            credential.credential_data = json.dumps(data)

        if not any(credential._use_secret_payload(self._credential_purpose).values()):
            super(MixinCredentialHolder, self.sudo()).write(
                {self._credential_holder_field: False}
            )
            credential.unlink()

    @api.model
    def _move_columns_into_credentials(self, doors) -> int:
        """Migrate the plain columns of `doors` into credentials, then drop them.

        Meant for a module's post-migration, once the doors replaced the columns
        in the registry. A dropped column does not linger in later backups the
        way a nulled one does.
        """
        field_map = self._credential_field_map()
        columns = {door: field_map[door] for door in doors}
        cr = self.env.cr
        cr.execute(
            SQL(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name = %s AND column_name = ANY(%s)",
                self._table,
                list(columns),
            )
        )
        present = [column for (column,) in cr.fetchall()]
        if not present:
            return 0
        cr.execute(
            SQL(
                "SELECT id, %s FROM %s WHERE %s",
                SQL(", ").join(SQL.identifier(column) for column in present),
                SQL.identifier(self._table),
                SQL(" OR ").join(
                    SQL(
                        "%s IS NOT NULL AND %s != ''",
                        SQL.identifier(c),
                        SQL.identifier(c),
                    )
                    for c in present
                ),
            )
        )
        rows = cr.fetchall()
        if (
            rows
            and not self.env["credential.credential"]._is_encryption_key_configured()
        ):
            raise UserError(
                self.env._(
                    "%(model)s holds secrets in plain columns that must move into "
                    "encrypted credentials. Set ODOO_API_ENCRYPTION_KEY and run the "
                    "upgrade again.",
                    model=self._description,
                )
            )
        records = self.sudo().with_context(active_test=False)
        for record_id, *values in rows:
            records.browse(record_id)._set_held_secrets(
                {
                    columns[column]: value
                    for column, value in zip(present, values, strict=True)
                    if value
                }
            )
        cr.execute(
            SQL(
                "ALTER TABLE %s %s",
                SQL.identifier(self._table),
                SQL(", ").join(
                    SQL("DROP COLUMN IF EXISTS %s", SQL.identifier(column))
                    for column in present
                ),
            )
        )
        _logger.info(
            "Moved the secrets of %s %s record(s) into credentials and dropped %s",
            len(rows),
            self._name,
            ", ".join(present),
        )
        return len(rows)
