import unittest


class TestBrAccountScaffold(unittest.TestCase):
    def test_module_imports(self):
        __import__("custom_addons.br_account")

