# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged, TagsSelector


@tagged('nodatabase')
class TestSetTags(TransactionCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @tagged()
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base'})

    def test_set_tags_not_decorated(self):
        """Test that a TransactionCase has some test_tags by default"""

        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base'})

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @tagged('slow')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base', 'slow'})

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @tagged('slow', 'nightly')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base', 'slow', 'nightly'})

    def test_inheritance(self):
        """Test inheritance when using the 'tagged' decorator"""

        @tagged('slow')
        class FakeClassA(TransactionCase):
            pass

        @tagged('nightly')
        class FakeClassB(FakeClassA):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base', 'nightly'})

        class FakeClassC(FakeClassA):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'base'})

    def test_untagging(self):
        """Test that one can remove the 'standard' tag"""

        @tagged('-standard')
        class FakeClassA(TransactionCase):
            pass

        fc = FakeClassA()
        self.assertEqual(fc.test_tags, {'at_install', 'base'})

        @tagged('-standard', '-base', '-at_install')
        class FakeClassB(TransactionCase):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, set())

        @tagged('-standard', '-base', '-at_install', 'fast')
        class FakeClassC(TransactionCase):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'fast', })


@tagged('nodatabase')
class TestSelector(TransactionCase):

    def test_selector_parser(self):
        """Test the parser part of the TagsSelector class"""

        tags = TagsSelector('+slow')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('+slow,nightly')
        self.assertEqual({'slow', 'nightly'}, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('+slow,-standard')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual({'standard', }, tags.exclude)

        # same with space after the comma
        tags = TagsSelector('+slow, -standard')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual({'standard', }, tags.exclude)

        # same with space befaore and after the comma
        tags = TagsSelector('+slow , -standard')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual({'standard', }, tags.exclude)

        tags = TagsSelector('+slow ,-standard,+js')
        self.assertEqual({'slow', 'js', }, tags.include)
        self.assertEqual({'standard', }, tags.exclude)

        tags = TagsSelector('slow, ')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('+slow,-standard, slow,-standard ')
        self.assertEqual({'slow', }, tags.include)
        self.assertEqual({'standard', }, tags.exclude)

        tags = TagsSelector('')
        self.assertEqual(set(), tags.include)
        self.assertEqual(set(), tags.exclude)

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

        @tagged('-at_install', 'post_install')
        class Test_E(TransactionCase):
            pass

        no_tags_obj = Test_A()
        stock_tag_obj = Test_B()
        multiple_tags_obj = Test_C()
        multiple_tags_standard_obj = Test_D()
        post_install_obj = Test_E()

        # if 'standard' in not explicitly removed, tests without tags are
        # considered tagged standard and they are run by default if
        # not explicitly deselected with '-standard' or if 'standard' is not
        # selectected along with another test tag

        # same as "--test-tags=''" parameters:
        tags = TagsSelector('')
        self.assertFalse(tags.check(no_tags_obj))

        # same as "--test-tags '+slow'":
        tags = TagsSelector('+slow')
        self.assertFalse(tags.check(no_tags_obj))

        # same as "--test-tags '+slow,+fake'":
        tags = TagsSelector('+slow,fake')
        self.assertFalse(tags.check(no_tags_obj))

        # same as "--test-tags '+slow,+standard'":
        tags = TagsSelector('slow,standard')
        self.assertTrue(no_tags_obj)

        # same as "--test-tags '+slow,-standard'":
        tags = TagsSelector('slow,-standard')
        self.assertFalse(tags.check(no_tags_obj))

        # same as "--test-tags '-slow,-standard'":
        tags = TagsSelector('-slow,-standard')
        self.assertFalse(tags.check(no_tags_obj))

        # same as "--test-tags '-slow,+standard'":
        tags = TagsSelector('-slow,+standard')
        self.assertTrue(tags.check(no_tags_obj))

        tags = TagsSelector('')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('slow')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('standard')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('slow,standard')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('slow,-standard')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('+stock')
        self.assertTrue(tags.check(stock_tag_obj))

        tags = TagsSelector('stock,fake')
        self.assertTrue(tags.check(stock_tag_obj))

        tags = TagsSelector('stock,standard')
        self.assertTrue(tags.check(stock_tag_obj))

        tags = TagsSelector('-stock')
        self.assertFalse(tags.check(stock_tag_obj))

        tags = TagsSelector('')
        self.assertFalse(tags.check(multiple_tags_obj))

        tags = TagsSelector('-stock')
        self.assertFalse(tags.check(multiple_tags_obj))

        tags = TagsSelector('-slow')
        self.assertFalse(tags.check(multiple_tags_obj))

        tags = TagsSelector('slow')
        self.assertTrue(tags.check(multiple_tags_obj))

        tags = TagsSelector('slow,stock')
        self.assertTrue(tags.check(multiple_tags_obj))

        tags = TagsSelector('-slow,stock')
        self.assertFalse(tags.check(multiple_tags_obj))

        tags = TagsSelector('slow,stock,-slow')
        self.assertFalse(tags.check(multiple_tags_obj))

        tags = TagsSelector('')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('standard')
        self.assertTrue(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('slow')
        self.assertTrue(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('slow,fake')
        self.assertTrue(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('-slow')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('-standard')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('-slow,-standard')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('standard,-slow')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        tags = TagsSelector('slow,-standard')
        self.assertFalse(tags.check(multiple_tags_standard_obj))

        # Mimic the real post_install use case
        # That uses a second tags selector
        tags = TagsSelector('standard')
        position = TagsSelector('post_install')
        self.assertTrue(tags.check(post_install_obj) and position.check(post_install_obj))
