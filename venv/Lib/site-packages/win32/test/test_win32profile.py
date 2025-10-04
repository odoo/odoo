"""Test win32profile"""

import os
import unittest

import win32profile


class Tester(unittest.TestCase):
    def test_environment(self):
        os.environ["FOO"] = "bar=baz"
        env = win32profile.GetEnvironmentStrings()
        self.assertIn("FOO", env)
        self.assertEqual(env["FOO"], "bar=baz")
        self.assertEqual(os.environ["FOO"], "bar=baz")


if __name__ == "__main__":
    unittest.main()
