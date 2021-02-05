# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.translit
"""

import unittest
import pytils
from pytils.third import six

class TranslitTestCase(unittest.TestCase):
    """
    Test case for pytils.translit
    """

    def ckTransl(self, in_, out_):
        """
        Checks translify
        """
        self.assertEquals(pytils.translit.translify(in_), out_)

    def ckDetransl(self, in_, out_):
        """
        Checks detranslify
        """
        self.assertEquals(pytils.translit.detranslify(in_), out_)

    def ckSlug(self, in_, out_):
        """
        Checks slugify
        """
        self.assertEquals(pytils.translit.slugify(in_), out_)

    def testTransliteration(self):
        """
        Unit-test for transliterations
        """
        self.ckTransl(u"тест", 'test')
        self.ckTransl(u"проверка", 'proverka')
        self.ckTransl(u"транслит", 'translit')
        self.ckTransl(u"правда ли это", 'pravda li eto')
        self.ckTransl(u"Щука", 'Schuka')

    def testTransliterationExceptions(self):
        """
        Unit-test for testing translify's exceptions
        """
        self.assertRaises(ValueError, pytils.translit.translify, u'\u00bfHabla espa\u00f1ol?')

    def testDetransliteration(self):
        """
        Unit-test for detransliterations
        """
        self.ckDetransl('test', u"тест")
        self.ckDetransl('proverka', u"проверка")
        self.ckDetransl('translit', u"транслит")
        self.ckDetransl('SCHuka', u"Щука")
        self.ckDetransl('Schuka', u"Щука")

    def testDetransliterationExceptions(self):
        """
        Unit-test for testing detranslify's exceptions
        """
        # for Python 2.x non-unicode detranslify should raise exception
        if six.PY2:
            self.assertRaises(ValueError, pytils.translit.detranslify, "тест")

    def testSlug(self):
        """
        Unit-test for slugs
        """
        self.ckSlug(u"ТеСт", 'test')
        self.ckSlug(u"Проверка связи", 'proverka-svyazi')
        self.ckSlug(u"me&you", 'me-and-you')
        self.ckSlug(u"и еще один тест", 'i-esche-odin-test')

    def testSlugExceptions(self):
        """
        Unit-test for testing slugify's exceptions
        """
        # for Python 2.x non-unicode slugify should raise exception
        if six.PY2:
            self.assertRaises(ValueError, pytils.translit.slugify, "тест")

    def testTranslifyAdditionalUnicodeSymbols(self):
        """
        Unit-test for testing additional unicode symbols
        """
        self.ckTransl(u"«Вот так вот»", '"Vot tak vot"')
        self.ckTransl(u"‘Или вот так’", "'Ili vot tak'")
        self.ckTransl(u"– Да…", "- Da...")

    def testSlugifyIssue10(self):
        """
        Unit-test for testing that bug#10 fixed
        """
        self.ckSlug(u"Проверка связи…", 'proverka-svyazi')
        self.ckSlug(u"Проверка\x0aсвязи 2", 'proverka-svyazi-2')
        self.ckSlug(u"Проверка\201связи 3", 'proverkasvyazi-3')

    def testSlugifyIssue15(self):
        """
        Unit-test for testing that bug#15 fixed
        """
        self.ckSlug(u"World of Warcraft", "world-of-warcraft")

    def testAdditionalDashesAndQuotes(self):
        """
        Unit-test for testing additional dashes (figure and em-dash)
        and quotes
        """
        self.ckSlug(u"Юнит-тесты — наше всё", 'yunit-testyi---nashe-vsyo')
        self.ckSlug(u"Юнит-тесты ‒ наше всё", 'yunit-testyi---nashe-vsyo')
        self.ckSlug(u"95−34", '95-34')
        self.ckTransl(u"Двигатель “Pratt&Whitney”", 'Dvigatel\' "Pratt&Whitney"')

if __name__ == '__main__':
    unittest.main()
