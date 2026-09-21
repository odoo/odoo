import tempfile
import unittest
from pathlib import Path
from unittest import mock

from odoo.tools.config import configmanager

CONF = """[options]
server_wide_modules = base,web,rust_engine
rust_engine_mode = on
rust_engine_mdoe = on
stray_key = 1
"""


class TestServerWideModulesClaimTheirFileOptions(unittest.TestCase):
    def setUp(self):
        self.config = configmanager()
        self.rcfile = Path(tempfile.mkdtemp()) / "odoo.conf"
        self.rcfile.write_text(CONF)

    def warnings_of(self, call):
        with mock.patch.object(configmanager, "_log") as log:
            call()
        return [args[1] % args[2:] for args, _kwargs in log.call_args_list]

    def load(self):
        return self.warnings_of(
            lambda: self.config._load_file_options(str(self.rcfile))
        )

    def unclaimed(self):
        return self.warnings_of(self.config.warn_unclaimed_file_options)

    def test_an_unowned_key_warns_at_load_and_an_owned_one_waits(self):
        output = self.load()
        self.assertEqual(len(output), 1)
        self.assertIn("'stray_key'", output[0])
        self.assertEqual(self.config["rust_engine_mode"], "on")

    def test_a_claimed_key_never_warns_and_a_typo_names_its_owner(self):
        self.load()
        self.config.claim_file_options("rust_engine_mode", "rust_engine_db")
        output = self.unclaimed()
        self.assertEqual(len(output), 1)
        self.assertIn("'rust_engine_mdoe'", output[0])
        self.assertIn("'rust_engine' did not claim it", output[0])
        self.assertEqual(self.unclaimed(), [])

    def test_a_claim_survives_a_reload(self):
        self.load()
        self.config.claim_file_options("rust_engine_mode")
        self.load()
        self.assertNotIn("rust_engine_mode", self.config._deferred_file_options)
        self.assertIn("rust_engine_mdoe", self.config._deferred_file_options)

    def test_the_command_line_names_the_owners_when_it_names_any(self):
        self.config._cli_options["server_wide_modules"] = ["base", "web"]
        output = self.load()
        self.assertEqual(len(output), 3)
        self.assertEqual(self.unclaimed(), [])
