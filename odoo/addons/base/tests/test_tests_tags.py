# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged, tag_test_selector


@tagged('nodatabase')
class TestSetTags(TransactionCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @tagged()
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base'})

    def test_set_tags_not_decorated(self):
        """Test that a TransactionCase has some test_tags by default"""

        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base'})

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @tagged('slow')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base', 'slow'})

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @tagged('slow', 'nightly')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base', 'slow', 'nightly'})

    def test_inheritance(self):
        """Test inheritance when using the 'tagged' decorator"""

        @tagged('slow')
        class FakeClassA(TransactionCase):
            pass

        @tagged('nightly')
        class FakeClassB(FakeClassA):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base', 'nightly'})

        class FakeClassC(FakeClassA):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'standard', 'at_install', 'base'})

    def test_untagging(self):
        """Test that one can remove the 'at_install' tag"""

        @tagged('-at_install')
        class FakeClassA(TransactionCase):
            pass

        fc = FakeClassA()
        self.assertEqual(fc.test_tags, {'standard', 'base'})

        @tagged('-at_install', '-base', '-standard')
        class FakeClassB(TransactionCase):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, set())

        @tagged('-at_install', '-base', 'fast')
        class FakeClassC(TransactionCase):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'fast', 'standard'})


@tagged('nodatabase')
class TestSelector(TransactionCase):

    def test_selector(self):
        """Test check_tags use cases"""
        class Test_A():
            pass

        @tagged('stock')
        class Test_B():
            pass

        @tagged('stock', 'slow')
        class Test_C():
            pass

        @tagged('at_install', 'slow')
        class Test_D():
            pass

        no_tags_obj = Test_A()
        stock_tag_obj = Test_B()
        multiple_tags_obj = Test_C()
        multiple_tags_at_install_obj = Test_D()

        # if 'at_install' in not explicitly removed, tests without tags are
        # considered tagged at_install and they are run by default if
        # not explicitly deselected with '-at_install' or if 'at_install' is not
        # selected along with another test tag

        # same as no "--test-tags" parameters:
        self.assertTrue(tag_test_selector(no_tags_obj, ''))

        # same as "--test-tags '+slow'":
        self.assertFalse(tag_test_selector(no_tags_obj, '+slow'))

        # same as "--test-tags '+slow,+fake'":
        self.assertFalse(tag_test_selector(no_tags_obj, '+slow,fake'))

        # same as "--test-tags '+slow,+at_install'":
        self.assertTrue(tag_test_selector(no_tags_obj, 'slow,at_install'))

        # same as "--test-tags '+slow,-at_install'":
        self.assertFalse(tag_test_selector(no_tags_obj, 'slow,-at_install'))

        # same as "--test-tags '-slow,-at_install'":
        self.assertFalse(tag_test_selector(no_tags_obj, '-slow,-at_install'))

        # same as "--test-tags '-slow,+at_install'":
        self.assertTrue(tag_test_selector(no_tags_obj, '-slow,+at_install'))

        self.assertFalse(tag_test_selector(stock_tag_obj, ''))
        self.assertFalse(tag_test_selector(stock_tag_obj, 'slow'))
        self.assertFalse(tag_test_selector(stock_tag_obj, 'at_install'))
        self.assertFalse(tag_test_selector(stock_tag_obj, 'slow,at_install'))
        self.assertFalse(tag_test_selector(stock_tag_obj, 'slow,-at_install'))
        self.assertTrue(tag_test_selector(stock_tag_obj, '+stock'))
        self.assertTrue(tag_test_selector(stock_tag_obj, 'stock,fake'))
        self.assertTrue(tag_test_selector(stock_tag_obj, 'stock,at_install'))
        self.assertFalse(tag_test_selector(stock_tag_obj, '-stock'))

        self.assertFalse(tag_test_selector(multiple_tags_obj, ''))
        self.assertFalse(tag_test_selector(multiple_tags_obj, '-stock'))
        self.assertFalse(tag_test_selector(multiple_tags_obj, '-slow'))
        self.assertTrue(tag_test_selector(multiple_tags_obj, 'slow'))
        self.assertTrue(tag_test_selector(multiple_tags_obj, 'slow,stock'))
        self.assertFalse(tag_test_selector(multiple_tags_obj, '-slow,stock'))
        self.assertFalse(tag_test_selector(multiple_tags_obj, 'slow,stock,-slow'))

        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, ''))
        self.assertTrue(tag_test_selector(multiple_tags_at_install_obj, 'at_install'))
        self.assertTrue(tag_test_selector(multiple_tags_at_install_obj, 'slow'))
        self.assertTrue(tag_test_selector(multiple_tags_at_install_obj, 'slow,fake'))
        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, '-slow'))
        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, '-at_install'))
        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, '-slow,-at_install'))
        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, 'at_install,-slow'))
        self.assertFalse(tag_test_selector(multiple_tags_at_install_obj, 'slow,-at_install'))

    def test_selector_post_install(self):
        """Test 'post_install' and 'at_install' special case"""

        # A at_install case that should run at install
        class Test_A(TransactionCase):
            pass

        # A post_install case that should only run 'post_install'
        @tagged('-at_install', 'post_install')
        class Test_B(TransactionCase):
            pass

        # A tagged post_install test that should run at 'post_install'
        @tagged('-at_install', 'post_install', 'slow')
        class Test_C(TransactionCase):
            pass

        # A tagged stndard test that should not run at 'post_install'
        @tagged('fast')
        class Test_D(TransactionCase):
            pass

        # Simulate "server.py" (post install)
        # without '--test-tags' -> default is 'at_install'
        self.assertFalse(tag_test_selector(Test_A, 'at_install,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_B, 'at_install,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_C, 'at_install,post_install,-at_install'))
        self.assertFalse(tag_test_selector(Test_D, 'at_install,post_install,-at_install'))

        # with '--test-tags 'slow''
        self.assertFalse(tag_test_selector(Test_A, 'slow,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_B, 'slow,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_C, 'slow,post_install,-at_install'))
        self.assertFalse(tag_test_selector(Test_D, 'slow,post_install,-at_install'))

        # with '--test-tags 'fast'
        self.assertFalse(tag_test_selector(Test_A, 'fast,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_B, 'fast,post_install,-at_install'))
        self.assertTrue(tag_test_selector(Test_C, 'fast,post_install,-at_install'))
        self.assertFalse(tag_test_selector(Test_D, 'fast,post_install,-at_install'))

        # simulate "loading.py" (right after a module is installed)
        # without '--test-tags' (at_install by default)
        self.assertTrue(tag_test_selector(Test_A, 'at_install,-post_install'))
        self.assertFalse(tag_test_selector(Test_B, 'at_install,-post_install'))
        self.assertFalse(tag_test_selector(Test_C, 'at_install,-post_install'))
        self.assertTrue(tag_test_selector(Test_D, 'at_install,-post_install'))

        # with '--test-tags 'slow''
        self.assertFalse(tag_test_selector(Test_A, 'slow,-post_install'))
        self.assertFalse(tag_test_selector(Test_B, 'slow,-post_install'))
        self.assertFalse(tag_test_selector(Test_C, 'slow,-post_install'))
        self.assertFalse(tag_test_selector(Test_D, 'slow,-post_install'))

        # with '--test-tags 'fast'
        self.assertFalse(tag_test_selector(Test_A, 'fast,-post_install'))
        self.assertFalse(tag_test_selector(Test_B, 'fast,-post_install'))
        self.assertFalse(tag_test_selector(Test_C, 'fast,-post_install'))
        self.assertTrue(tag_test_selector(Test_D, 'fast,-post_install'))

        # with '--test-tags '-fast'
        self.assertFalse(tag_test_selector(Test_A, '-fast,-post_install'))
        self.assertFalse(tag_test_selector(Test_B, '-fast,-post_install'))
        self.assertFalse(tag_test_selector(Test_C, '-fast,-post_install'))
        self.assertFalse(tag_test_selector(Test_D, '-fast,-post_install'))

        # test the post_install use case the way it really works (with two selectors)
        self.assertTrue(tag_test_selector(Test_C, 'post_install') and tag_test_selector(Test_C, 'standard'))
        self.assertFalse(tag_test_selector(Test_A, 'post_install') and tag_test_selector(Test_A, 'standard'))
        self.assertTrue(tag_test_selector(Test_A, 'at_install') and tag_test_selector(Test_A, 'standard'))