import sys
import optparse
import logging

from collections import defaultdict

from . import Command
from odoo.modules.registry import Registry
from odoo.tools import SQL, config

_logger = logging.getLogger(__name__)


class Obfuscate(Command):
    """Obfuscate data in a given odoo database"""
    def __init__(self):
        super().__init__()
        self.cr = None

    def _ensure_cr(func):
        def check_cr(self, *args, **kwargs):
            if not self.cr:
                raise Exception("No database connection")
            return func(self, *args, **kwargs)
        return check_cr

    @_ensure_cr
    def begin(self):
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
        self.cr.execute("INSERT INTO ir_config_parameter (key, value) VALUES ('odoo_cyph_pwd', 'odoo_cyph_'||encode(pgp_sym_encrypt(%s, %s), 'base64')) ON CONFLICT(key) DO NOTHING", [pwd, pwd])

    @_ensure_cr
    def check_pwd(self, pwd):
        """If password is set, check if it's valid"""
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
        """Unset password to cypher/uncypher datas"""
        self.cr.execute("DELETE FROM ir_config_parameter WHERE key='odoo_cyph_pwd' ")

    def cypher_string(self, sql_field: SQL, password):
        # don't double cypher fields
        return SQL("""CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_') THEN %(field_name)s ELSE 'odoo_cyph_'||encode(pgp_sym_encrypt(%(field_name)s, %(pwd)s), 'base64') END""", field_name=sql_field, pwd=password)

    def uncypher_string(self, sql_field: SQL, password):
        return SQL("""CASE WHEN starts_with(%(field_name)s, 'odoo_cyph_') THEN pgp_sym_decrypt(decode(substring(%(field_name)s, 11)::text, 'base64'), %(pwd)s) ELSE %(field_name)s END""", field_name=sql_field, pwd=password)

    def check_field(self, table, field):
        qry = "SELECT udt_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s"
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
        qry = "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND udt_name IN ['text', 'varchar', 'jsonb'] AND NOT table_name LIKE 'ir_%' ORDER BY 1,2"
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
                self.cr.execute(SQL('select distinct jsonb_object_keys(%s) as key from %s', sql_field, SQL.identifier(table)))
                keys = [k[0] for k in self.cr.fetchall()]
                for key in keys:
                    cypher_query = cyph_fct(SQL("%s->>%s", sql_field, key), pwd)
                    new_field_value = SQL(
                        """jsonb_set(%s, array[%s], to_jsonb(%s)::jsonb, FALSE)""",
                        new_field_value, key, cypher_query
                    )
                cypherings.append(SQL('%s=%s', sql_field, new_field_value))

        if cypherings:
            query = SQL("UPDATE %s SET %s", SQL.identifier(table), SQL(',').join(cypherings))
            self.cr.execute(query)
            if with_commit:
                self.commit()
                self.begin()

    def confirm_not_secure(self):
        _logger.info("The obfuscate method is not considered as safe to transfer anonymous datas to a third party.")
        conf_y = input(f"This will alter data in the database {self.dbname} and can lead to a data loss. Would you like to proceed [y/N]? ")
        if conf_y.upper() != 'Y':
            self.rollback()
            sys.exit(0)
        conf_db = input(f"Please type your database name ({self.dbname}) in UPPERCASE to confirm you understand this operation is not considered secure : ")
        if self.dbname.upper() != conf_db:
            self.rollback()
            sys.exit(0)
        return True

    def run(self, cmdargs):
        parser = config.parser
        parser.prog = self.prog
        group = optparse.OptionGroup(parser, "Obfuscate Configuration")
        group.add_option('--pwd', dest="pwd", default=False, help="Cypher password")
        group.add_option('--fields', dest="fields", default=False, help="List of table.columns to obfuscate/unobfuscate: table1.column1,table2.column1,table2.column2")
        group.add_option('--exclude', dest="exclude", default=False, help="List of table.columns to exclude from obfuscate/unobfuscate: table1.column1,table2.column1,table2.column2")
        group.add_option('--file', dest="file", default=False, help="File containing the list of table.columns to obfuscate/unobfuscate")
        group.add_option('--unobfuscate', action='store_true', default=False)
        group.add_option('--allfields', action='store_true', default=False, help="Used in unobfuscate mode, try to unobfuscate all fields. Cannot be used in obfuscate mode. Slower than specifying fields.")
        group.add_option('--vacuum', action='store_true', default=False, help="Vacuum database after unobfuscating")
        group.add_option('--pertablecommit', action='store_true', default=False, help="Commit after each table instead of a big transaction")
        group.add_option(
            '-y', '--yes', dest="yes", action='store_true', default=False,
            help="Don't ask for manual confirmation. Use it carefully as the obfuscate method is not considered as safe to transfer anonymous datas to a third party.")

        parser.add_option_group(group)
        if not cmdargs:
            sys.exit(parser.print_help())

        try:
            opt = config.parse_config(cmdargs, setup_logging=True)
            if not opt.pwd:
                _logger.error("--pwd is required")
                sys.exit("ERROR: --pwd is required")
            if opt.allfields and not opt.unobfuscate:
                _logger.error("--allfields can only be used in unobfuscate mode")
                sys.exit("ERROR: --allfields can only be used in unobfuscate mode")
            self.dbname = config['db_name']
            self.registry = Registry(self.dbname)
            with self.registry.cursor() as cr:
                self.cr = cr
                self.begin()
                if self.check_pwd(opt.pwd):
                    fields = [
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

                    if opt.fields:
                        if not opt.allfields:
                            fields += [tuple(f.split('.')) for f in opt.fields.split(',')]
                        else:
                            _logger.error("--allfields option is set, ignoring --fields option")
                    if opt.file:
                        with open(opt.file, encoding='utf-8') as f:
                            fields += [tuple(l.strip().split('.')) for l in f]
                    if opt.exclude:
                        if not opt.allfields:
                            fields = [f for f in fields if f not in [tuple(f.split('.')) for f in opt.exclude.split(',')]]
                        else:
                            _logger.error("--allfields option is set, ignoring --exclude option")

                    if opt.allfields:
                        fields = self.get_all_fields()
                    else:
                        invalid_fields = [f for f in fields if not self.check_field(f[0], f[1])]
                        if invalid_fields:
                            _logger.error("Invalid fields: %s", ', '.join([f"{f[0]}.{f[1]}" for f in invalid_fields]))
                            fields = [f for f in fields if f not in invalid_fields]

                    if not opt.unobfuscate and not opt.yes:
                        self.confirm_not_secure()

                    _logger.info("Processing fields: %s", ', '.join([f"{f[0]}.{f[1]}" for f in fields]))
                    tables = defaultdict(set)

                    for t, f in fields:
                        if t[0:3] != 'ir_' and '.' not in t:
                            tables[t].add(f)

                    if opt.unobfuscate:
                        _logger.info("Unobfuscating datas")
                        for table in tables:
                            _logger.info("Unobfuscating table %s", table)
                            self.convert_table(table, tables[table], opt.pwd, opt.pertablecommit, True)

                        if opt.vacuum:
                            _logger.info("Vacuuming obfuscated tables")
                            for table in tables:
                                _logger.debug("Vacuuming table %s", table)
                                self.cr.execute(SQL("VACUUM FULL %s", SQL.identifier(table)))
                        self.clear_pwd()
                    else:
                        _logger.info("Obfuscating datas")
                        self.set_pwd(opt.pwd)
                        for table in tables:
                            _logger.info("Obfuscating table %s", table)
                            self.convert_table(table, tables[table], opt.pwd, opt.pertablecommit)

                    self.commit()
                else:
                    self.rollback()

        except Exception as e:  # noqa: BLE001
            sys.exit("ERROR: %s" % e)
