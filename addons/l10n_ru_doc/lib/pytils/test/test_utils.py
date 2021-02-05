# -*- coding: utf-8 -*-
"""
Unit-tests for pytils.utils
"""

import unittest
import pytils
import decimal

    

class ChecksTestCase(unittest.TestCase):
    """
    Test case for check_* utils
    """
        
    def testCheckLength(self):
        """
        Unit-test for pytils.utils.check_length
        """
        self.assertEquals(pytils.utils.check_length("var", 3), None)
        
        self.assertRaises(ValueError, pytils.utils.check_length, "var", 4)
        self.assertRaises(ValueError, pytils.utils.check_length, "var", 2)
        self.assertRaises(ValueError, pytils.utils.check_length, (1,2), 3)

    def testCheckPositive(self):
        """
        Unit-test for pytils.utils.check_positive
        """
        self.assertEquals(pytils.utils.check_positive(0), None)
        self.assertEquals(pytils.utils.check_positive(1), None)
        self.assertEquals(pytils.utils.check_positive(1, False), None)
        self.assertEquals(pytils.utils.check_positive(1, strict=False), None)
        self.assertEquals(pytils.utils.check_positive(1, True), None)
        self.assertEquals(pytils.utils.check_positive(1, strict=True), None)
        self.assertEquals(pytils.utils.check_positive(decimal.Decimal("2.0")), None)
        self.assertEquals(pytils.utils.check_positive(2.0), None)
        
        self.assertRaises(ValueError, pytils.utils.check_positive, -2)
        self.assertRaises(ValueError, pytils.utils.check_positive, -2.0)
        self.assertRaises(ValueError, pytils.utils.check_positive, decimal.Decimal("-2.0"))
        self.assertRaises(ValueError, pytils.utils.check_positive, 0, True)


class SplitValuesTestCase(unittest.TestCase):
    
    def testClassicSplit(self):
        """
        Unit-test for pytils.utils.split_values, classic split
        """
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u"Раз,Два,Три"))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u"Раз, Два,Три"))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u" Раз,   Два, Три  "))
        self.assertEquals((u"Раз", u"Два", u"Три"), pytils.utils.split_values(u" Раз, \nДва,\n Три  "))
    
    def testEscapedSplit(self):
        """
        Unit-test for pytils.utils.split_values, split with escaping
        """
        self.assertEquals((u"Раз,Два", u"Три,Четыре", u"Пять,Шесть"), pytils.utils.split_values(u"Раз\,Два,Три\,Четыре,Пять\,Шесть"))
        self.assertEquals((u"Раз, Два", u"Три", u"Четыре"), pytils.utils.split_values(u"Раз\, Два, Три, Четыре"))

if __name__ == '__main__':
    unittest.main()
