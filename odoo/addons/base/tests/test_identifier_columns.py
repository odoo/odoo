from odoo.tests import TransactionCase, tagged
from odoo.tools import SQL

#: fields whose name says they store the id of a record, whatever their type
RES_ID_SUFFIXES = ('res_id',)


@tagged('post_install', '-at_install')
class TestIdentifierColumns(TransactionCase):
    """ Columns holding the id of a record must be as wide as the ids the
    database produces, whether the field declares the relation (many2one,
    many2one_reference) or only stores the number (res_id and friends). """

    def _column_types(self):
        """ Return {(table, column): type} for every column in the schema. """
        self.env.cr.execute(SQL("""
            SELECT c.relname, a.attname, format_type(a.atttypid, NULL)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
            AND n.nspname = current_schema
        """))
        return {(row[0], row[1]): row[2] for row in self.env.cr.fetchall()}

    def _identifier_fields(self):
        """ Yield the stored fields that hold the id of a record. """
        for model_name, model in self.env.registry.items():
            if model._abstract or model._transient or not model._auto:
                continue
            for field in self.env[model_name]._fields.values():
                if not field.store or not field.column_type:
                    continue
                if field.company_dependent or field.translate:
                    continue  # stored as jsonb
                if field.type in ('many2one', 'many2one_reference') or field.name.endswith(RES_ID_SUFFIXES):
                    yield model_name, field

    def test_identifier_columns_are_wide_enough(self):
        """ every column holding a record id has the width of the database """
        expected = 'bigint' if self.env.registry.id_column_type[0] == 'int8' else 'integer'
        columns = self._column_types()
        narrow = []
        for model_name, field in self._identifier_fields():
            table = self.env[model_name]._table
            actual = columns.get((table, field.name))
            if actual is None:
                continue  # the column is not in this database
            if actual != expected:
                narrow.append(f"{model_name}.{field.name} ({table}.{field.name}) is {actual}")
        self.assertFalse(narrow, (
            "these columns hold a record id but are not %s; a many2one or a "
            "many2one_reference gets the width on its own, a plain Integer "
            "needs bigint=True:\n  %s" % (expected, "\n  ".join(sorted(narrow)))
        ))

    def test_res_id_fields_are_declared(self):
        """ a field named res_id must declare that it holds an id """
        undeclared = []
        for model_name, field in self._identifier_fields():
            if field.type != 'integer' or not field.name.endswith(RES_ID_SUFFIXES):
                continue
            if not field.bigint:
                undeclared.append(f"{model_name}.{field.name}")
        self.assertFalse(undeclared, (
            "these Integer fields store a record id and must be declared with "
            "bigint=True so their column follows the width of the database:\n  %s"
            % "\n  ".join(sorted(undeclared))
        ))

    def test_every_identifier_field_resolves_to_the_database_width(self):
        """ the width comes from the database, never from the declared type

        A many2one_reference declares int8 and marks itself as holding an id,
        while an Integer does it through bigint=True; both must end up asking
        the registry, or a column created on an existing database would not
        match the ones already there.
        """
        expected = self.env.registry.id_column_type
        wrong = []
        for model_name, field in self._identifier_fields():
            model = self.env[model_name]
            if field.company_dependent or field.translate:
                continue
            if field.db_column_type(model) != expected:
                wrong.append(f"{model_name}.{field.name} ({field.type}) -> {field.db_column_type(model)}")
        self.assertFalse(wrong, (
            "these fields resolve to a width the database does not use:\n  %s"
            % "\n  ".join(sorted(wrong))
        ))

    def test_foreign_keys_do_not_mix_widths(self):
        """ no foreign key points from one width to the other """
        self.env.cr.execute(SQL("""
            SELECT c.relname, a.attname, rc.relname, r.attname
            FROM pg_constraint fk
            JOIN pg_class c ON c.oid = fk.conrelid
            JOIN pg_class rc ON rc.oid = fk.confrelid
            JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = ANY (fk.conkey)
            JOIN pg_attribute r ON r.attrelid = fk.confrelid AND r.attnum = ANY (fk.confkey)
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE fk.contype = 'f' AND a.atttypid <> r.atttypid
            AND n.nspname = current_schema
        """))
        mixed = [f"{row[0]}.{row[1]} -> {row[2]}.{row[3]}" for row in self.env.cr.fetchall()]
        self.assertFalse(mixed, (
            "these foreign keys have a different type on each side, so the "
            "referencing column cannot hold every id of the table it points "
            "to:\n  %s" % "\n  ".join(sorted(mixed))
        ))
