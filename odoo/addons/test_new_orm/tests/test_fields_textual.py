from unittest.mock import patch


from odoo import Command
from odoo.exceptions import UserError

from odoo.tests import TransactionCase, tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHtmlField(TransactionCase):

    def setUp(self):
        super().setUp()
        self.model = self.env['test_orm.mixed']

    def test_00_sanitize(self):
        self.assertEqual(self.model._fields['comment1'].sanitize, False)
        self.assertEqual(self.model._fields['comment2'].sanitize_attributes, True)
        self.assertEqual(self.model._fields['comment2'].strip_classes, False)
        self.assertEqual(self.model._fields['comment3'].sanitize_attributes, True)
        self.assertEqual(self.model._fields['comment3'].strip_classes, True)

        some_ugly_html = """<p>Oops this should maybe be sanitized
% if object.some_field and not object.oriented:
<table>
    % if object.other_field:
    <tr style="margin: 0px; border: 10px solid black;">
        ${object.mako_thing}
        <td>
    </tr>
    <tr class="custom_class">
        This is some html.
    </tr>
    % endif
    <tr>
%if object.dummy_field:
        <p>Youpie</p>
%endif"""

        record = self.model.create({
            'comment1': some_ugly_html,
            'comment2': some_ugly_html,
            'comment3': some_ugly_html,
            'comment4': some_ugly_html,
        })

        self.assertEqual(record.comment1, some_ugly_html, 'Error in HTML field: content was sanitized but field has sanitize=False')

        self.assertIn('<tr class="', record.comment2)

        # sanitize should have closed tags left open in the original html
        self.assertIn('</table>', record.comment3, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('</td>', record.comment3, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('<tr style="', record.comment3, 'Style attr should not have been stripped')
        # sanitize does not keep classes if asked to
        self.assertNotIn('<tr class="', record.comment3)

        self.assertNotIn('<tr style="', record.comment4, 'Style attr should have been stripped')

    def test_01_sanitize_groups(self):
        self.assertEqual(self.model._fields['comment5'].sanitize, True)
        self.assertEqual(self.model._fields['comment5'].sanitize_overridable, True)

        internal_user = self.env['res.users'].create({
            'name': 'test internal user',
            'login': 'test_sanitize',
            'group_ids': [(6, 0, [self.ref('base.group_user')])],
        })
        bypass_user = self.env['res.users'].create({
            'name': 'test bypass user',
            'login': 'test_sanitize2',
            'group_ids': [(6, 0, [self.ref('base.group_user'), self.ref('base.group_sanitize_override')])],
        })
        record = self.env['test_orm.mixed'].create({})

        # 1. Test normalize case: diff due to normalize should not prevent the
        #    changes
        val = '<blockquote>Something</blockquote>'
        normalized_val = '<blockquote data-o-mail-quote-node="1" data-o-mail-quote="1">Something</blockquote>'
        write_vals = {'comment5': val}

        record.with_user(internal_user).write(write_vals)
        self.assertEqual(record.comment5, normalized_val,
                         "should be normalized (not in groups)")
        record.with_user(bypass_user).write(write_vals)
        self.assertEqual(record.comment5, val,
                         "should not be normalized (has group)")
        record.with_user(internal_user).write(write_vals)
        self.assertEqual(record.comment5, normalized_val,
                         "should be normalized (not in groups) despite admin previous diff")

        # 2. Test main use case: prevent restricted user to wipe non restricted
        #    user previous change
        val = '<script></script>'
        write_vals = {'comment5': val}

        record.with_user(internal_user).write(write_vals)
        self.assertEqual(record.comment5, '',
                         "should be sanitized (not in groups)")
        record.with_user(bypass_user).write(write_vals)
        self.assertEqual(record.comment5, val,
                         "should not be sanitized (has group)")
        with self.assertRaises(UserError):
            # should crash (not in groups and sanitize would break content of
            # other user that bypassed the sanitize)
            record.with_user(internal_user).write(write_vals)

        # 3. Make sure field compare in `_convert` is working as expected with
        #    special content / format
        val = '<span  attr1 ="att1"   attr2=\'attr2\'>é@&nbsp;</span><p><span/></p>'
        write_vals = {'comment5': val}
        # Once sent through `html_sanitize()` this is becoming:
        # `<span attr1="att1" attr2="attr2">é@\xa0</span><p><span></span></p>`
        # Notice those change:
        # -     `attr1 =` -> `attr1=`    (space before `=`)
        # -    `   attr2` -> ` attr2`    (multi space -> single space)
        # -  `=\'attr2\'` -> `="attr2"`  (escaped single quote -> double quote)
        # -      `&nbsp;` -> `\xa0`
        # Still, those 2 archs should be considered equals and not raise

        record.with_user(bypass_user).write(write_vals)
        # Next write shouldn't raise a sanitize right error
        record.with_user(internal_user).write(write_vals)

        # 4. Ensure our exception handling is fine
        val = '<!-- I am a comment -->'
        write_vals = {'comment5': val}
        record.with_user(internal_user).write(write_vals)
        self.assertEqual(record.comment5, '',
                         "should be sanitized (not in groups)")

        # extra test with new record having 'record' as origin
        new_record = record.new(origin=record)
        new_record.with_user(bypass_user).comment5

        # this was causing an infinite recursion (see explanation in fields.py)
        new_record.invalidate_recordset()
        new_record.with_user(internal_user).comment5

    @patch('odoo.orm.fields_textual.html_sanitize', return_value='<p>comment</p>')
    def test_onchange_sanitize(self, patch):
        self.assertTrue(self.registry['test_orm.mixed'].comment2.sanitize)

        record = self.env['test_orm.mixed'].create({
            'comment2': '<p>comment</p>',
        })

        # the new value is sanitized upon insertion in db,
        # but not put in cache, therefore not sanitized a second time
        self.assertEqual(patch.call_count, 1)

        # new value sanitized for insertion in cache
        record.comment2 = '<p>comment</p>'
        self.assertEqual(patch.call_count, 2)

        # the value in cache is dirty -> convert_to_column_update(..., validate=False),
        # so no additional call to `html_sanitize`
        record.flush_recordset()
        self.assertEqual(patch.call_count, 2)

        # value coming from db does not need to be sanitized
        record.invalidate_recordset()
        record.comment2
        self.assertEqual(patch.call_count, 2)

        # value coming from db during an onchange does not need to be sanitized
        new_record = record.new(origin=record)
        new_record.comment2
        self.assertEqual(patch.call_count, 2)
