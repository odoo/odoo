from odoo.tests import tagged
from odoo.tools import SQL

from odoo.addons.mail.tests.common import MailCommon


@tagged('mail_track')
class TestTrackingValueWidth(MailCommon):
    """ old_value_integer and new_value_integer hold the id of a tracked
    many2one, next to its display name in the char column, so they must be
    able to store any identifier the database can produce and not only the
    ones that fit in a 32-bit integer. """

    def _column_type(self, column):
        self.env.cr.execute(SQL(
            """ SELECT format_type(a.atttypid, NULL)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'mail_tracking_value'
                AND c.relnamespace = current_schema::regnamespace
                AND a.attname = %s AND a.attnum > 0 """,
            column,
        ))
        return self.env.cr.fetchone()[0]

    def test_value_integer_follows_the_database(self):
        """ the columns have the width the database uses for identifiers """
        model = self.env['mail.tracking.value']
        expected = 'bigint' if self.env.registry.id_column_type[0] == 'int8' else 'integer'
        for column in ('old_value_integer', 'new_value_integer'):
            with self.subTest(column=column):
                self.assertEqual(self._column_type(column), expected)
                field = model._fields[column]
                self.assertTrue(field.bigint, "the field must be declared as holding an id")
                self.assertEqual(field.db_column_type(model), self.env.registry.id_column_type)

    def test_value_integer_holds_a_large_id(self):
        """ the columns accept an identifier beyond the 32-bit range """
        if self.env.registry.id_column_type[0] != 'int8':
            self.skipTest("the database uses 32-bit identifiers")

        message = self.env['mail.message'].create({'subject': 'tracking'})
        large_id = 2 ** 31 + 12345
        tracking = self.env['mail.tracking.value'].create({
            'mail_message_id': message.id,
            'old_value_integer': large_id,
            'new_value_integer': large_id + 1,
        })
        tracking.invalidate_recordset()
        self.assertEqual(tracking.old_value_integer, large_id)
        self.assertEqual(tracking.new_value_integer, large_id + 1)
