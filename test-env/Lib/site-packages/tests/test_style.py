import unittest
import sys

import style


class StyleTestCase(unittest.TestCase):

    def test_argument_on_root_style_builder(self):
        # test if a call of the root StyleBuilder raises a TypeError
        with self.assertRaises(TypeError):
            style('test')

    def test_enabled(self):
        # test if enabled by default
        self.assertTrue(style.enabled)

    def test_single_string(self):
        # test styling of single string
        self.assertIn('test', style.red('test'))
        self.assertIn('31', str(style.red('test')))

    def test_multiple_strings(self):
        # test styling of multiple strings
        self.assertIn('test1 test2', style.red('test1', 'test2'))
        self.assertIn('31', str(style.red('test1', 'test2')))

    def test_non_string_arguments(self):
        # test styling of multiple arguments that are not strings
        self.assertIn('1 True 0.1', style.red(1, True, 0.1))
        self.assertIn('31', str(style.red(1, True, 0.1)))

    def test_seperator(self):
        # test custom seperator
        self.assertIn('test1, test2', style.red('test1', 'test2', sep=', '))

    def test_non_string_seperator(self):
        # test if a non string seperator raises a TypeError
        with self.assertRaises(TypeError):
            style.red('test1', 'test2', sep=0)

    def test_style_chaining(self):
        # test that chaining style attributes works
        self.assertIn('31;47;1', str(style.red.on_white.bold('test')))
        self.assertIn('47;31;1', str(style.on_white.red.bold('test')))
        self.assertIn('47;1;31', str(style.on_white.bold.red('test')))

    def test_len(self):
        # test if the lenght is independet of the style
        styled_string = style.red('test')

        self.assertEqual(len(styled_string), len('test'))
        self.assertTrue(len(str(styled_string)) > len(styled_string))

    def test_enabling(self):
        # test manually enabling and disabling
        style.enabled = False
        self.assertEqual('test', style.red('test'))

        style.enabled = True
        self.assertIn('test', str(style.red('test')))
        self.assertIn('31', str(style.red('test')))
