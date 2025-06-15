import unittest
import warnings
import sys

# All supported python versions now provide SSLContext.
# We subclass without importing by name. Compare with
# warning2.py
import ssl

class MySubclass(ssl.SSLContext):
    pass

# This file should only have this one test in it
# because we have to be careful about our imports
# and because we need to be careful about our patching.

class Test(unittest.TestCase):

    @unittest.skipIf(sys.version_info[:2] < (3, 6),
                     "Only on Python 3.6+")
    def test_ssl_subclass_and_module_reference(self):

        from gevent import monkey

        self.assertFalse(monkey.saved)

        with warnings.catch_warnings(record=True) as issued_warnings:
            warnings.simplefilter('always')

            monkey.patch_all()
            monkey.patch_all()

        issued_warnings = [x for x in issued_warnings
                           if isinstance(x.message, monkey.MonkeyPatchWarning)]

        self.assertEqual(1, len(issued_warnings))
        message = str(issued_warnings[0].message)

        self.assertNotIn("Modules that had direct imports", message)
        self.assertIn("Subclasses (NOT patched)", message)
        # the gevent subclasses should not be in here.
        self.assertNotIn('gevent.', message)



if __name__ == '__main__':
    unittest.main()
