# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged, BaseCase
from odoo.tests.tag_selector import TagsSelector


@tagged('nodatabase')
class TestSetTags(TransactionCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @tagged()
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'at_install', 'standard'})
        self.assertEqual(fc.test_module, 'base')

    def test_set_tags_not_decorated(self):
        """Test that a TransactionCase has some test_tags by default"""

        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, {'at_install', 'standard'})
        self.assertEqual(fc.test_module, 'base')

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @tagged('slow')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'slow'})
        self.assertEqual(fc.test_module, 'base')

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @tagged('slow', 'nightly')
        class FakeClass(TransactionCase):
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'slow', 'nightly'})
        self.assertEqual(fc.test_module, 'base')

    def test_inheritance(self):
        """Test inheritance when using the 'tagged' decorator"""

        @tagged('slow')
        class FakeClassA(TransactionCase):
            pass

        class FakeClassC(FakeClassA):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'at_install', 'standard', 'slow'})

        @tagged('-standard')
        class FakeClassD(FakeClassA):
            pass

        fc = FakeClassD()
        self.assertEqual(fc.test_tags, {'at_install', 'slow'})

    def test_untagging(self):
        """Test that one can remove the 'standard' tag"""

        @tagged('-standard')
        class FakeClassA(TransactionCase):
            pass

        fc = FakeClassA()
        self.assertEqual(fc.test_tags, {'at_install'})
        self.assertEqual(fc.test_module, 'base')

        @tagged('-standard', '-base', '-at_install', 'post_install')
        class FakeClassB(TransactionCase):
            pass

        fc = FakeClassB()
        self.assertEqual(fc.test_tags, {'post_install'})

        @tagged('-standard', '-base', 'fast')
        class FakeClassC(TransactionCase):
            pass

        fc = FakeClassC()
        self.assertEqual(fc.test_tags, {'fast', 'at_install'})

    def test_parental_advisory(self):
        """Explicit test tags on the class should override anything
        """
        @tagged('flow')
        class FakeClassA(TransactionCase):
            pass
        class FakeClassB(FakeClassA):
            test_tags = {'foo', 'bar'}

        self.assertEqual(FakeClassA().test_tags, {'standard', 'at_install', 'flow'})
        self.assertEqual(FakeClassB().test_tags, {'foo', 'bar'})

@tagged('nodatabase')
class TestSelector(TransactionCase):

    def test_selector_parser(self):
        """Test the parser part of the TagsSelector class"""

        tags = TagsSelector('+slow')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('+slow,nightly')
        self.assertEqual({('slow', None, None, None, None), ('nightly', None, None, None, None)}, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('+slow,-standard')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)

        # same with space after the comma
        tags = TagsSelector('+slow, -standard')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)

        # same with space before and after the comma
        tags = TagsSelector('+slow , -standard')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)

        tags = TagsSelector('+slow ,-standard,+js')
        self.assertEqual({('slow', None, None, None, None), ('js', None, None, None, None)}, tags.include)
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)

        # without +
        tags = TagsSelector('slow, ')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        # duplicates
        tags = TagsSelector('+slow,-standard, slow,-standard ')
        self.assertEqual({('slow', None, None, None, None), }, tags.include)
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)

        tags = TagsSelector('')
        self.assertEqual(set(), tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('/module')  # all standard test of a module
        self.assertEqual({('standard', 'module', None, None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('/module/tests/test_file.py')  # all standard test of a module
        self.assertEqual({('standard', None, None, None, 'module.tests.test_file'), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('*/module')  # all tests of a module
        self.assertEqual({(None, 'module', None, None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector(':class')  # all standard test of a class
        self.assertEqual({('standard', None, 'class', None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('.method')
        self.assertEqual({('standard', None, None, 'method', None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector(':class.method')
        self.assertEqual({('standard', None, 'class', 'method', None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('/module:class.method')  # only a specific test func in a module (standard)
        self.assertEqual({('standard', 'module', 'class', 'method', None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('*/module:class.method')  # only a specific test func in a module
        self.assertEqual({(None, 'module', 'class', 'method', None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('-/module:class.method')  # disable a specific test func in a module
        self.assertEqual({('standard', None, None, None, None), }, tags.include)  # all strandard
        self.assertEqual({(None, 'module', 'class', 'method', None), }, tags.exclude)  # exept the test func

        tags = TagsSelector('-*/module:class.method') 
        self.assertEqual({('standard', None, None, None, None), }, tags.include)
        self.assertEqual({(None, 'module', 'class', 'method', None), }, tags.exclude)

        tags = TagsSelector('tag/module')
        self.assertEqual({('tag', 'module', None, None, None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('tag.method')
        self.assertEqual({('tag', None, None, 'method', None), }, tags.include)
        self.assertEqual(set(), tags.exclude)

        tags = TagsSelector('*/module,-standard')  # all non standard test of a module
        self.assertEqual({(None, 'module', None, None, None), }, tags.include)  # all in module
        self.assertEqual({('standard', None, None, None, None), }, tags.exclude)  # exept standard ones


@tagged('nodatabase')
class TestSelectorSelection(TransactionCase):
    def test_selector_selection(self):
        """Test check_tags use cases"""
        class Test_A(TransactionCase):
            pass

        @tagged('stock')
        class Test_B(BaseCase):
            pass

        @tagged('stock', 'slow')
        class Test_C(BaseCase):
            pass

        @tagged('standard', 'slow')
        class Test_D(BaseCase):
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
        self.assertTrue(tags.check(stock_tag_obj))

        tags = TagsSelector('slow,standard')
        self.assertTrue(tags.check(stock_tag_obj))

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
