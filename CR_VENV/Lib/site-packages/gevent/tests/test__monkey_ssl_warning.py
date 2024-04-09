import unittest
import warnings

# This file should only have this one test in it
# because we have to be careful about our imports
# and because we need to be careful about our patching.

class Test(unittest.TestCase):

    def test_with_pkg_resources(self):
        # Issue 1108: Python 2, importing pkg_resources,
        # as is done for namespace packages, imports ssl,
        # leading to an unwanted SSL warning.
        __import__('pkg_resources')

        from gevent import monkey

        self.assertFalse(monkey.saved)

        with warnings.catch_warnings(record=True) as issued_warnings:
            warnings.simplefilter('always')

            monkey.patch_all()
            monkey.patch_all()

        issued_warnings = [x for x in issued_warnings
                           if isinstance(x.message, monkey.MonkeyPatchWarning)]

        self.assertFalse(issued_warnings, [str(i) for i in issued_warnings])
        self.assertEqual(0, len(issued_warnings))


if __name__ == '__main__':
    unittest.main()
