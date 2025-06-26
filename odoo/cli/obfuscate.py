import argparse
import logging
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

from odoo.modules.registry import Registry
from odoo.tools import SQL, config

from .command import PROG_NAME, Command

_logger = logging.getLogger(__name__)

DEFAULT_FIELDS = [
    ('mail_tracking_value', 'old_value_char'),
    ('mail_tracking_value', 'old_value_text'),
    ('mail_tracking_value', 'new_value_char'),
    ('mail_tracking_value', 'new_value_text'),
    ('res_partner', 'name'),
    ('res_partner', 'complete_name'),
    ('res_partner', 'email'),
    ('res_partner', 'phone'),
    ('res_partner', 'mobile'),
    ('res_partner', 'street'),
    ('res_partner', 'street2'),
    ('res_partner', 'city'),
    ('res_partner', 'zip'),
    ('res_partner', 'vat'),
    ('res_partner', 'website'),
    ('res_country', 'name'),
    ('mail_message', 'subject'),
    ('mail_message', 'email_from'),
    ('mail_message', 'reply_to'),
    ('mail_message', 'body'),
    ('crm_lead', 'name'),
    ('crm_lead', 'contact_name'),
    ('crm_lead', 'partner_name'),
    ('crm_lead', 'email_from'),
    ('crm_lead', 'phone'),
    ('crm_lead', 'mobile'),
    ('crm_lead', 'website'),
    ('crm_lead', 'description'),
]


class Obfuscate(Command):
    """Obfuscate data in a given odoo database"""

    def _ensure_cr(func):
        def check_cr(self, *args, **kwargs):
            if not self.cr:
                raise Exception("No database connection")
            return func(self, *args, **kwargs)
        return check_cr

    @_ensure_cr
    def begin(self):
        self.cr.execute("BEGIN WORK")
        self.cr.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    @_ensure_cr
    def commit(self):
        self.cr.commit()

    @_ensure_cr
    def rollback(self):
        self.cr.rollback()

    @_ensure_cr
    def set_pwd(self, pwd):
        """ Set password to cypher/uncypher datas """
        self.cr.execute("""
            INSERT INTO ir_config_parameter (key, value)
                 VALUES ('odoo_cyph_pwd', 'odoo_cyph_' || encode(pgp_sym_encrypt(%s, %s), 'base64'))
            ON CONFLICT (key) DO NOTHING
        """, [pwd, pwd])

    @_ensure_cr
    def check_pwd(self, pwd):
        """ If password is set, check if it's valid """
        uncypher_pwd = self.uncypher_string(SQL.identifier('value'), pwd)

        try:
            query = SQL("SELECT %s FROM ir_config_parameter WHERE key='odoo_cyph_pwd'", uncypher_pwd)
            self.cr.execute(query)
            if self.cr.rowcount == 0 or (self.cr.rowcount == 1 and self.cr.fetchone()[0] == pwd):
                return True
        except Exception as e:  # noqa: BLE001
            _logger.error("Error checking password: %s", e)
        return False

    @_ensure_cr
    def clear_pwd(self):
        """ Unset password to cypher/uncypher datas """
        self.cr.execute("DELETE FROM ir_config_parameter WHERE key='odoo_cyph_pwd' ")

    def cypher_string(self, sql_field: SQL, password):
        # don't double cypher fields
        return SQL("""
              CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_')
                   THEN %(field_name)s
                   ELSE 'odoo_cyph_'||encode(pgp_sym_encrypt(%(field_name)s, %(pwd)s), 'base64')
              END
        """, field_name=sql_field, pwd=password)

    def uncypher_string(self, sql_field: SQL, password):
        return SQL("""
              CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_')
                   THEN pgp_sym_decrypt(decode(substring(%(field_name)s, 11)::text, 'base64'), %(pwd)s)
                   ELSE %(field_name)s
              END
        """, field_name=sql_field, pwd=password)

    def check_field(self, table, field):
        qry = """
            SELECT udt_name
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = %s
        """
        self.cr.execute(qry, [table, field])
        if self.cr.rowcount == 1:
            res = self.cr.fetchone()
            if res[0] in ['text', 'varchar']:
                # Doesn t work for selection fields ...
                return 'string'
            if res[0] == 'jsonb':
                return 'json'
        return False

    def get_all_fields(self):
        qry = """
            SELECT table_name,
                   column_name
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND udt_name IN ['text', 'varchar', 'jsonb']
               AND NOT table_name LIKE 'ir_%'
             ORDER BY 1, 2
        """
        self.cr.execute(qry)
        return self.cr.fetchall()

    def convert_table(self, table, fields, pwd, with_commit=False, unobfuscate=False):
        cypherings = []
        cyph_fct = self.uncypher_string if unobfuscate else self.cypher_string

        for field in fields:
            field_type = self.check_field(table, field)
            sql_field = SQL.identifier(field)
            if field_type == 'string':
                cypher_query = cyph_fct(sql_field, pwd)
                cypherings.append(SQL('%s=%s', SQL.identifier(field), cypher_query))
            elif field_type == 'json':
                # List every key
                # Loop on keys
                # Nest the jsonb_set calls to update all values at once
                # Do not create the key in json if doesn't esist
                new_field_value = sql_field
                self.cr.execute(SQL("""
                    SELECT DISTINCT jsonb_object_keys(%s) AS key FROM %s
                """, sql_field, SQL.identifier(table)))
                keys = [k[0] for k in self.cr.fetchall()]
                for key in keys:
                    cypher_query = cyph_fct(SQL("%s->>%s", sql_field, key), pwd)
                    new_field_value = SQL(
                        "jsonb_set(%s, array[%s], to_jsonb(%s)::jsonb, FALSE)",
                        new_field_value, key, cypher_query,
                    )
                cypherings.append(SQL('%s=%s', sql_field, new_field_value))

        if cypherings:
            query = SQL("UPDATE %s SET %s", SQL.identifier(table), SQL(',').join(cypherings))
            self.cr.execute(query)
            if with_commit:
                self.commit()
                self.begin()

    def confirm_not_secure(self):
        print(textwrap.dedent(  # noqa: T201
            f"""\
                {PROG_NAME}: obfuscation is ** not ** a secure way to anonymize data in your database before sending to a third party.
                Please carefully review every step to avoid leaking any sensitive information.
                This procedure will alter data in the database {self.dbname!r} and can lead to data loss.
            """))
        questions = ((
            "Would you like to proceed? (y/N): "
        ), (
            "This operation is not considered secure.\n"
            f"Please type your database name {self.dbname!r} in UPPERCASE to confirm: "
        ))
        expected_answer_sets = (
            {'Y', 'y'},
            {self.dbname.upper()},
        )

        for question, expected_answer_set in zip(questions, expected_answer_sets):
            answer = (input(textwrap.dedent(question)) or '').strip()
            print()  # noqa: T201
            if answer not in expected_answer_set:
                _logger.error("Operation cancelled by user")
                return False

        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parser.formatter_class = argparse.RawTextHelpFormatter
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        self.parser.add_argument(
            '--pwd', required=True,
            help="Obfuscation password")
        self.parser.add_argument(
            '--fields', metavar='TABLE.COLUMN,...',
            help=textwrap.dedent("""\
                Comma separated list of 'table.columns' to obfuscate/unobfuscate.
                i.e.: table1.column1,table2.column1,table2.column2
            """))
        self.parser.add_argument(
            '--exclude', metavar='TABLE.COLUMN,...',
            help=textwrap.dedent("""\
                Comma separated list of 'table.columns' to exclude from obfuscate/unobfuscate.
                i.e.: table1.column1,table2.column1,table2.column2
            """))
        self.parser.add_argument(
            '--file', type=Path,
            help="File containing the list of table.columns to obfuscate/unobfuscate")
        self.parser.add_argument(
            '--unobfuscate', action='store_true')
        self.parser.add_argument(
            '--allfields', action='store_true',
            help=textwrap.dedent("""\
                Used in unobfuscate mode, try to unobfuscate all fields.
                Cannot be used in obfuscate mode. Slower than specifying fields.
            """))
        self.parser.add_argument(
            '--vacuum', action='store_true',
            help="Vacuum database after unobfuscating")
        self.parser.add_argument(
            '--pertablecommit', action='store_true',
            help="Commit after each table instead of a big transaction")
        self.parser.add_argument(
            '-y', '--yes', action='store_true',
            help=textwrap.dedent("""\
                Don't ask for manual confirmation. Use it carefully as the obfuscate
                method is not considered as safe to transfer anonymous data to a
                third party."""))

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = []
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]
        config.parse_config(config_args, setup_logging=True)

        db_names = config['db_name']
        if not db_names or len(db_names) > 1:
            self.parser.error("Please provide a single database")
        self.dbname = parsed_args.db_name = db_names[0]

        # Ask for confirm when obfuscating
        if not parsed_args.unobfuscate and not parsed_args.yes:
            if not self.confirm_not_secure():
                sys.exit(0)

        def record_split(fields_str, sep=','):
            return [
                tuple(record.strip().split('.'))
                for record in (fields_str or '').split(sep)
            ]

        # Get fields
        if parsed_args.allfields:
            if not parsed_args.unobfuscate:
                self.parser.error("--allfields can only be used in unobfuscate mode")
            if parsed_args.fields:
                _logger.error("--allfields option is set, the --fields option will be ignored")
            if parsed_args.exclude:
                _logger.error("--allfields option is set, the --exclude option will be ignored")
            fields = []
        else:
            fields = [
                field for field in [
                    *DEFAULT_FIELDS,
                    *record_split(parsed_args.fields),
                    *(record_split(Path.read_text(parsed_args.file), '\n') if parsed_args.file else []),
                ]
                if field not in record_split(parsed_args.exclude)
            ]

        with Registry(self.dbname).cursor() as cr:
            self.cr = cr

            self.begin()
            if not self.check_pwd(parsed_args.pwd):
                self.rollback()
                sys.exit(0)
            if parsed_args.allfields:
                fields = self.get_all_fields()
            else:
                invalid_fields = [f for f in fields if not self.check_field(f[0], f[1])]
                if invalid_fields:
                    _logger.error("Invalid fields: %s", ', '.join([f"{f[0]}.{f[1]}" for f in invalid_fields]))
                    fields = [f for f in fields if f not in invalid_fields]

            _logger.info("Processing fields: %s", ', '.join([f"{f[0]}.{f[1]}" for f in fields]))
            tables = defaultdict(set)

            for t, f in fields:
                if t[0:3] != 'ir_' and '.' not in t:
                    tables[t].add(f)

            if parsed_args.unobfuscate:
                _logger.info("Unobfuscating data")
                for table in tables:
                    _logger.info("Unobfuscating table %s", table)
                    self.convert_table(table, tables[table], parsed_args.pwd, parsed_args.pertablecommit, True)

                if parsed_args.vacuum:
                    _logger.info("Vacuuming obfuscated tables")
                    for table in tables:
                        _logger.debug("Vacuuming table %s", table)
                        self.cr.execute(SQL("VACUUM FULL %s", SQL.identifier(table)))
                self.clear_pwd()

            else:
                _logger.info("Obfuscating data")
                self.set_pwd(parsed_args.pwd)
                for table in tables:
                    _logger.info("Obfuscating table %s", table)
                    self.convert_table(table, tables[table], parsed_args.pwd, parsed_args.pertablecommit)

            self.commit()
