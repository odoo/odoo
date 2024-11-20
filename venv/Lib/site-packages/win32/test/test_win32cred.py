import copy
import unittest

import win32cred


class TestCredFunctions(unittest.TestCase):

    def setUp(self):
        self.flags = 0
        self.dummy_cred = {
            "TargetName": "DumyyUser",
            "Type": win32cred.CRED_TYPE_GENERIC,
            "Flags": self.flags,
        }

    def create_dummy_cred(self):
        cred = copy.deepcopy(self.dummy_cred)
        cred.update(
            {
                "Persist": win32cred.CRED_PERSIST_SESSION,
            }
        )
        try:
            win32cred.CredWrite(cred, self.flags)
        except Exception as e:
            print(e)

    def is_dummy_cred(self):
        return (
            len(
                [
                    e
                    for e in win32cred.CredEnumerate()
                    if e["TargetName"] == self.dummy_cred["TargetName"]
                ]
            )
            == 1
        )

    def test_creddelete(self):
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertIsNone(win32cred.CredDelete(**self.dummy_cred))
        self.assertFalse(self.is_dummy_cred())
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertIsNone(win32cred.CredDelete(*self.dummy_cred.values()))
        self.assertFalse(self.is_dummy_cred())
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertIsNone(
            win32cred.CredDelete(self.dummy_cred["TargetName"], self.dummy_cred["Type"])
        )
        self.assertFalse(self.is_dummy_cred())
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertIsNone(win32cred.CredDelete(self.dummy_cred))
        self.assertFalse(self.is_dummy_cred())
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertIsNone(win32cred.CredDelete(Target=self.dummy_cred))
        self.assertFalse(self.is_dummy_cred())
        self.create_dummy_cred()
        self.assertTrue(self.is_dummy_cred())
        self.assertRaises(TypeError, win32cred.CredDelete, "")
        self.assertRaises(KeyError, win32cred.CredDelete, {})
        self.assertRaises(KeyError, win32cred.CredDelete, {"TargetName": ""})
        self.assertRaises(
            TypeError, win32cred.CredDelete, {"TargetName": "", "Type": 3.141593}
        )
        self.assertIsNone(win32cred.CredDelete(self.dummy_cred))
        self.assertFalse(self.is_dummy_cred())

    def test_credgetsessiontypes(self):
        res = win32cred.CredGetSessionTypes()
        self.assertEqual(len(res), win32cred.CRED_TYPE_MAXIMUM)
        for i in range(1, len(res)):
            self.assertEqual(res[:i], win32cred.CredGetSessionTypes(i))
            self.assertEqual(
                res[:i], win32cred.CredGetSessionTypes(MaximumPersistCount=i)
            )
        self.assertRaises(
            ValueError,
            win32cred.CredGetSessionTypes,
            0,
        )
        self.assertRaises(
            ValueError,
            win32cred.CredGetSessionTypes,
            MaximumPersistCount=win32cred.CRED_TYPE_MAXIMUM + 1,
        )
