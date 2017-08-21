# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged, TagsTestSelector, TagsError


@tagged('nodatabase')
class TestSetTags(TransactionCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @tagged()
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'standard', 'base'})

    def test_set_tags_not_decorated(self):
        """Test that a TransactionCase has some test_tags by default"""

        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'standard', 'base'})

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @tagged('slow')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'standard', 'base', 'slow'})

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @tagged('slow', 'nightly')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'standard', 'base', 'slow', 'nightly'})

    def test_set_tags_unallowed_chars(self):
        """Test the set_tags decorator with unallowed chars"""

        with self.assertRaises(TagsError):
            @tagged('+slow')
            class FakeClassA():
                pass

        with self.assertRaises(TagsError):
            @tagged('js+slow')
            class FakeClassB():
                pass

        with self.assertRaises(TagsError):
            @tagged('')
            class FakeClassC():
                pass

        with self.assertRaises(TagsError):
            @tagged('js ')
            class FakeClassD():
                pass

        with self.assertRaises(TagsError):
            @tagged(242)
            class FakeClassE():
                pass

        @tagged('-slow1')  # test that '-' is allowed as long as alnum chars
        class FakeClassE():
            pass

    def test_inheritance(self):
        """Test inheritance when using the 'tagged' decorator"""

        @tagged('slow')
        class FakeClassA(TransactionCase):
            pass

        @tagged('nightly')
        class FakeClassB(FakeClassA):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, {'standard', 'base', 'nightly'})

        class FakeClassC(FakeClassA):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'standard', 'base'})

    def test_untagging(self):
        """Test that one can remove the 'standard' tag"""

        @tagged('-standard')
        class FakeClassA(TransactionCase):
            pass

        fc = FakeClassA()
        self.assertEqual(fc.test_tags, {'base', })

        @tagged('-standard', '-base')
        class FakeClassB(TransactionCase):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, set())

        @tagged('-standard', '-base', 'fast')
        class FakeClassC(TransactionCase):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'fast', })


@tagged('nodatabase')
class TestSelector(TransactionCase):

    def test_selector_parser(self):
        """Test the parser part of the TagsTestSelector class"""

        select = TagsTestSelector('+slow')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual(set(), select.exclude)

        select = TagsTestSelector('+slow,nightly')
        self.assertEqual({'slow', 'nightly'}, select.include)
        self.assertEqual(set(), select.exclude)

        select = TagsTestSelector('+slow,-standard')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual({'standard', }, select.exclude)

        # same with space after the comma
        select = TagsTestSelector('+slow, -standard')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual({'standard', }, select.exclude)

        # same with space befaore and after the comma
        select = TagsTestSelector('+slow , -standard')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual({'standard', }, select.exclude)

        select = TagsTestSelector('+slow ,-standard,+js')
        self.assertEqual({'slow', 'js', }, select.include)
        self.assertEqual({'standard', }, select.exclude)

        select = TagsTestSelector('slow, ')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual(set(), select.exclude)

        select = TagsTestSelector('+slow,-standard, slow,-standard ')
        self.assertEqual({'slow', }, select.include)
        self.assertEqual({'standard', }, select.exclude)

        select = TagsTestSelector('')
        self.assertEqual({'standard', }, select.include)
        self.assertEqual(set(), select.exclude)

@tagged('nodatabase')
class TestSelectorSelection(TransactionCase):

    def test_selector_selection(self):
        """Test check_tags use cases"""
        class Test_A(TransactionCase):
            pass

        @tagged('stock')
        class Test_B():
            pass

        @tagged('stock', 'slow')
        class Test_C():
            pass

        @tagged('standard', 'slow')
        class Test_D():
            pass

        no_tags_obj = Test_A()
        stock_tag_obj = Test_B()
        multiple_tags_obj = Test_C()
        multiple_tags_standard_obj = Test_D()

        # if 'standard' in not explicitly removed, tests without tags are
        # considered tagged standards and they are run by default if
        # not explicitly deselected with '-standards' or if 'standards' is not
        # selectected along with another test tag

        # same as no "--test-tags" parameters:
        select = TagsTestSelector('')
        self.assertTrue(select(no_tags_obj))

        # same as "--test-tags '+slow'":
        select = TagsTestSelector('+slow')
        self.assertFalse(select(no_tags_obj))

        # same as "--test-tags '+slow,+fake'":
        select = TagsTestSelector('+slow,fake')
        self.assertFalse(select(no_tags_obj))

        # same as "--test-tags '+slow,+standard'":
        select = TagsTestSelector('slow,standard')
        self.assertTrue(no_tags_obj)

        # same as "--test-tags '+slow,-standard'":
        select = TagsTestSelector('slow,-standard')
        self.assertFalse(select(no_tags_obj))

        # same as "--test-tags '-slow,-standard'":
        select = TagsTestSelector('-slow,-standard')
        self.assertFalse(select(no_tags_obj))

        # same as "--test-tags '-slow,+standard'":
        select = TagsTestSelector('-slow,+standard')
        self.assertTrue(select(no_tags_obj))

        select = TagsTestSelector('')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('slow')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('standard')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('slow,standard')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('slow,-standard')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('+stock')
        self.assertTrue(select(stock_tag_obj))

        select = TagsTestSelector('stock,fake')
        self.assertTrue(select(stock_tag_obj))

        select = TagsTestSelector('stock,standard')
        self.assertTrue(select(stock_tag_obj))

        select = TagsTestSelector('-stock')
        self.assertFalse(select(stock_tag_obj))

        select = TagsTestSelector('')
        self.assertFalse(select(multiple_tags_obj))

        select = TagsTestSelector('-stock')
        self.assertFalse(select(multiple_tags_obj))

        select = TagsTestSelector('-slow')
        self.assertFalse(select(multiple_tags_obj))

        select = TagsTestSelector('slow')
        self.assertTrue(select(multiple_tags_obj))

        select = TagsTestSelector('slow,stock')
        self.assertTrue(select(multiple_tags_obj))

        select = TagsTestSelector('-slow,stock')
        self.assertFalse(select(multiple_tags_obj))

        select = TagsTestSelector('slow,stock,-slow')
        self.assertFalse(select(multiple_tags_obj))

        select = TagsTestSelector('')
        self.assertTrue(select(multiple_tags_standard_obj))

        select = TagsTestSelector('standard')
        self.assertTrue(select(multiple_tags_standard_obj))

        select = TagsTestSelector('slow')
        self.assertTrue(select(multiple_tags_standard_obj))

        select = TagsTestSelector('slow,fake')
        self.assertTrue(select(multiple_tags_standard_obj))

        select = TagsTestSelector('-slow')
        self.assertFalse(select(multiple_tags_standard_obj))

        select = TagsTestSelector('-standard')
        self.assertFalse(select(multiple_tags_standard_obj))

        select = TagsTestSelector('-slow,-standard')
        self.assertFalse(select(multiple_tags_standard_obj))

        select = TagsTestSelector('stantard,-slow')
        self.assertFalse(select(multiple_tags_standard_obj))

        select = TagsTestSelector('slow,-standard')
        self.assertFalse(select(multiple_tags_standard_obj))
