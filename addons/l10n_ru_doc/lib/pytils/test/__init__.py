# -*- coding: utf-8 -*-
"""
Unit tests for pytils
"""
__all__ = ["test_numeral", "test_dt", "test_translit", "test_utils", "test_typo"]

import unittest
import sys

def get_django_suite():
    try:
        import django
    except ImportError:
        return unittest.TestSuite()
    
    import pytils.test.templatetags
    return pytils.test.templatetags.get_suite()

def get_suite():
    """Return TestSuite for all unit-test of pytils"""
    suite = unittest.TestSuite()
    for module_name in __all__:
        imported_module = __import__("pytils.test."+module_name,
                                       globals(),
                                       locals(),
                                       ["pytils.test"])
        
        loader = unittest.defaultTestLoader
        suite.addTest(loader.loadTestsFromModule(imported_module))
        suite.addTest(get_django_suite())

    return suite

def run_tests_from_module(module, verbosity=1):
    """Run unit-tests for single module"""
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    suite.addTest(loader.loadTestsFromModule(module))
    unittest.TextTestRunner(verbosity=verbosity).run(suite)

def run(verbosity=1):
    """Run all unit-test of pytils"""
    suite = get_suite()
    res = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    if res.errors or res.failures:
        sys.exit(1)

if __name__ == '__main__':
    run(2)

