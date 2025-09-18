import functools
import logging
import pathlib
import sys
from collections import defaultdict

from odoo.modules.registry import Registry
from odoo.tools import SQL, config

from . import Command
from .command import build_config_args

_logger = logging.getLogger(__name__)


class Obfuscate(Command):
    """Obfuscate data in a given odoo database"""

    def __init__(self):
        super().__init__()
        self.cr = None

    @staticmethod  # NOTE: intentional — class-scoped decorator, works because Python
    # resolves _ensure_cr from local namespace during class body execution before
    # the staticmethod descriptor wrapping takes effect.
    def _ensure_cr(func):
        """Decorator that ensures a database cursor is available."""

        @functools.wraps(func)
        def check_cr(self, *args, **kwargs):
            if not self.cr:
                msg = "No database connection"
                raise RuntimeError(msg)
            return func(self, *args, **kwargs)

        return check_cr

    @_ensure_cr
    def begin(self):
        # NOTE: "BEGIN WORK" is redundant with psycopg's autocommit=False (auto-transaction),
        # but works in practice (PG issues a harmless warning). Left as-is since this tool
        # handles production data encryption and the transaction flow is battle-tested.
        self.cr.execute("begin work")
        self.cr.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    @_ensure_cr
    def commit(self):
        self.cr.commit()

    @_ensure_cr
    def rollback(self):
        self.cr.rollback()

    @_ensure_cr
    def set_pwd(self, pwd):
        """Set password to cypher/uncypher datas"""
        self.cr.execute(
            "INSERT INTO ir_config_parameter (key, value) VALUES ('odoo_cyph_pwd', 'odoo_cyph_'||encode(pgp_sym_encrypt(%s, %s), 'base64')) ON CONFLICT(key) DO NOTHING",
            [pwd, pwd],
        )

    @_ensure_cr
    def check_pwd(self, pwd):
        """If password is set, check if it's valid"""
        uncypher_pwd = self.uncypher_string(SQL.identifier("value"), pwd)

        try:
            query = SQL(
                "SELECT %s FROM ir_config_parameter WHERE key='odoo_cyph_pwd'",
                uncypher_pwd,
            )
            self.cr.execute(query)
            if self.cr.rowcount == 0 or (
                self.cr.rowcount == 1 and self.cr.fetchone()[0] == pwd
            ):
                return True
        except Exception as e:
            _logger.error("Error checking password: %s", e)
        return False

    @_ensure_cr
    def clear_pwd(self):
        """Unset password to cypher/uncypher datas"""
        self.cr.execute("DELETE FROM ir_config_parameter WHERE key='odoo_cyph_pwd' ")

    def cypher_string(self, sql_field: SQL, password):
        # don't double cypher fields
        return SQL(
            """CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_') THEN %(field_name)s ELSE 'odoo_cyph_'||encode(pgp_sym_encrypt(%(field_name)s, %(pwd)s), 'base64') END""",
            field_name=sql_field,
            pwd=password,
        )

    def uncypher_string(self, sql_field: SQL, password):
        return SQL(
            """CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_') THEN pgp_sym_decrypt(decode(substring(%(field_name)s, 11)::text, 'base64'), %(pwd)s) ELSE %(field_name)s END""",
            field_name=sql_field,
            pwd=password,
        )

    def check_field(self, table, field):
        qry = "SELECT udt_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s AND table_schema = current_schema"
        self.cr.execute(qry, [table, field])
        if self.cr.rowcount == 1:
            res = self.cr.fetchone()
            if res[0] in ["text", "varchar"]:
                # Doesn t work for selection fields ...
                return "string"
            if res[0] == "jsonb":
                return "json"
        return False

    def get_all_fields(self):
        qry = (
            "SELECT table_name, column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema AND udt_name IN ('text', 'varchar', 'jsonb') AND NOT table_name LIKE 'ir_%' ORDER BY 1,2"
        )
        self.cr.execute(qry)
        return self.cr.fetchall()

    def convert_table(self, table, fields, pwd, with_commit=False, unobfuscate=False):
        cypherings = []
        cyph_fct = self.uncypher_string if unobfuscate else self.cypher_string

        for field in fields:
            field_type = self.check_field(table, field)
            sql_field = SQL.identifier(field)
            if field_type == "string":
                cypher_query = cyph_fct(sql_field, pwd)
                cypherings.append(SQL("%s=%s", SQL.identifier(field), cypher_query))
            elif field_type == "json":
                # List every key
                # Loop on keys
                # Nest the jsonb_set calls to update all values at once
                # Do not create the key in json if doesn't esist
                new_field_value = sql_field
                self.cr.execute(
                    SQL(
                        "select distinct jsonb_object_keys(%s) as key from %s",
                        sql_field,
                        SQL.identifier(table),
                    )
                )
                keys = [k[0] for k in self.cr.fetchall()]
                for key in keys:
                    cypher_query = cyph_fct(SQL("%s->>%s", sql_field, key), pwd)
                    new_field_value = SQL(
                        """jsonb_set(%s, array[%s], to_jsonb(%s)::jsonb, FALSE)""",
                        new_field_value,
                        key,
                        cypher_query,
                    )
                cypherings.append(SQL("%s=%s", sql_field, new_field_value))

        if cypherings:
            query = SQL(
                "UPDATE %s SET %s",
                SQL.identifier(table),
                SQL(",").join(cypherings),
            )
            self.cr.execute(query)
            if with_commit:
                self.commit()
                self.begin()

    def confirm_not_secure(self):
        _logger.info(
            "The obfuscate method is not considered as safe to transfer anonymous datas to a third party."
        )
        conf_y = input(
            f"This will alter data in the database {self.dbname} and can lead to a data loss. Would you like to proceed [y/N]? "
        )
        if conf_y.upper() != "Y":
            self.rollback()
            sys.exit(0)
        conf_db = input(
            f"Please type your database name ({self.dbname}) in UPPERCASE to confirm you understand this operation is not considered secure : "
        )
        if self.dbname.upper() != conf_db:
            self.rollback()
            sys.exit(0)
        return True

    def run(self, cmdargs):
        parser = self.parser
        self.add_config_arguments(parser)
        parser.add_argument("--pwd", required=True, help="Cypher password")
        parser.add_argument(
            "--fields",
            default=None,
            help="List of table.columns to obfuscate/unobfuscate: table1.column1,table2.column1,table2.column2",
        )
        parser.add_argument(
            "--exclude",
            default=None,
            help="List of table.columns to exclude from obfuscate/unobfuscate: table1.column1,table2.column1,table2.column2",
        )
        parser.add_argument(
            "--file",
            default=None,
            help="File containing the list of table.columns to obfuscate/unobfuscate",
        )
        parser.add_argument("--unobfuscate", action="store_true", default=False)
        parser.add_argument(
            "--allfields",
            action="store_true",
            default=False,
            help="Used in unobfuscate mode, try to unobfuscate all fields. Cannot be used in obfuscate mode. Slower than specifying fields.",
        )
        parser.add_argument(
            "--vacuum",
            action="store_true",
            default=False,
            help="Vacuum database after unobfuscating",
        )
        parser.add_argument(
            "--pertablecommit",
            action="store_true",
            default=False,
            help="Commit after each table instead of a big transaction",
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            default=False,
            help="Don't ask for manual confirmation.",
        )

        if not cmdargs:
            sys.exit(parser.print_help())

        opt = parser.parse_args(cmdargs)

        if opt.allfields and not opt.unobfuscate:
            parser.error("--allfields can only be used in unobfuscate mode")

        config_args = build_config_args(opt.config, opt.db_name)
        config.parse_config(config_args, setup_logging=True)
        self.dbname = self.require_single_database(opt)

        try:
            self.registry = Registry(self.dbname)
            with self.registry.cursor() as cr:
                self.cr = cr
                self.begin()
                if self.check_pwd(opt.pwd):
                    fields = [
                        ("mail_tracking_value", "old_value_char"),
                        ("mail_tracking_value", "old_value_text"),
                        ("mail_tracking_value", "new_value_char"),
                        ("mail_tracking_value", "new_value_text"),
                        ("res_partner", "name"),
                        ("res_partner", "complete_name"),
                        ("res_partner", "email"),
                        ("res_partner", "phone"),
                        ("res_partner", "mobile"),
                        ("res_partner", "street"),
                        ("res_partner", "street2"),
                        ("res_partner", "city"),
                        ("res_partner", "zip"),
                        ("res_partner", "vat"),
                        ("res_partner", "website"),
                        ("res_country", "name"),
                        ("mail_message", "subject"),
                        ("mail_message", "email_from"),
                        ("mail_message", "reply_to"),
                        ("mail_message", "body"),
                        ("crm_lead", "name"),
                        ("crm_lead", "contact_name"),
                        ("crm_lead", "partner_name"),
                        ("crm_lead", "email_from"),
                        ("crm_lead", "phone"),
                        ("crm_lead", "mobile"),
                        ("crm_lead", "website"),
                        ("crm_lead", "description"),
                    ]

                    if opt.fields:
                        if not opt.allfields:
                            fields += [
                                tuple(f.split(".")) for f in opt.fields.split(",")
                            ]
                        else:
                            _logger.error(
                                "--allfields option is set, ignoring --fields option"
                            )
                    if opt.file:
                        with pathlib.Path(opt.file).open(encoding="utf-8") as f:
                            fields += [tuple(l.strip().split(".")) for l in f]
                    if opt.exclude:
                        if not opt.allfields:
                            fields = [
                                f
                                for f in fields
                                if f
                                not in [
                                    tuple(f.split(".")) for f in opt.exclude.split(",")
                                ]
                            ]
                        else:
                            _logger.error(
                                "--allfields option is set, ignoring --exclude option"
                            )

                    if opt.allfields:
                        fields = self.get_all_fields()
                    else:
                        invalid_fields = [
                            f for f in fields if not self.check_field(f[0], f[1])
                        ]
                        if invalid_fields:
                            _logger.error(
                                "Invalid fields: %s",
                                ", ".join([f"{f[0]}.{f[1]}" for f in invalid_fields]),
                            )
                            fields = [f for f in fields if f not in invalid_fields]

                    if not opt.unobfuscate and not opt.yes:
                        self.confirm_not_secure()

                    _logger.info(
                        "Processing fields: %s",
                        ", ".join([f"{f[0]}.{f[1]}" for f in fields]),
                    )
                    tables = defaultdict(set)

                    for t, f in fields:
                        if not t.startswith("ir_") and "." not in t:
                            tables[t].add(f)

                    if opt.unobfuscate:
                        _logger.info("Unobfuscating datas")
                        for table in tables:
                            _logger.info("Unobfuscating table %s", table)
                            self.convert_table(
                                table,
                                tables[table],
                                opt.pwd,
                                opt.pertablecommit,
                                True,
                            )

                        if opt.vacuum:
                            _logger.info("Vacuuming obfuscated tables")
                            for table in tables:
                                _logger.debug("Vacuuming table %s", table)
                                self.cr.execute(
                                    SQL("VACUUM FULL %s", SQL.identifier(table))
                                )
                        self.clear_pwd()
                    else:
                        _logger.info("Obfuscating datas")
                        self.set_pwd(opt.pwd)
                        for table in tables:
                            _logger.info("Obfuscating table %s", table)
                            self.convert_table(
                                table,
                                tables[table],
                                opt.pwd,
                                opt.pertablecommit,
                            )

                    self.commit()
                else:
                    self.rollback()

        except Exception as e:
            sys.exit(f"ERROR: {e}")
