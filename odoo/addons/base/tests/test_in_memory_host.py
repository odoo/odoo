from odoo.tests.in_memory_case import InMemoryCase

from .test_config_parameter import TestSetGetParam, TestTypedParams


class TestTypedParamsInMemory(InMemoryCase, TestTypedParams):
    # the module's own test class on the DB-free tier: the body is
    # test_config_parameter.py's, only the base class differs
    hosts_modules = ("base",)


class TestSetGetParamInMemory(InMemoryCase, TestSetGetParam):
    hosts_modules = ("base",)

    def test_set_param_create_race(self):
        self.skipTest("opens a second cursor to race the INSERT: DB-bound by design")


class TestTheHostIsTheDbFreeTier(InMemoryCase):
    # what makes the two classes above meaningful: they ran on the tier, not
    # on the database the odoo-bin run is otherwise using
    def test_the_environment_is_in_memory_and_carries_bases_data(self):
        from odoo.orm.model_test_env import InMemoryCursor

        self.assertIsInstance(self.env.cr, InMemoryCursor)
        self.assertEqual(self.env.cr.dbname, ":memory:")
        self.assertGreater(len(self.registry.models), 140)
        self.assertGreater(self.env["ir.model.access"].sudo().search_count([]), 150)
        self.assertEqual(self.env.ref("base.user_admin").login, "admin")

    def test_a_write_is_rolled_back_between_tests(self):
        self.env["ir.config_parameter"].sudo().set_param("base.host_probe", "seen")
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("base.host_probe"), "seen"
        )

    def test_the_previous_tests_write_is_gone(self):
        # alphabetical order runs `test_a_write...` first; its row must not
        # have survived the per-test savepoint
        self.assertFalse(
            self.env["ir.config_parameter"].sudo().get_param("base.host_probe")
        )
