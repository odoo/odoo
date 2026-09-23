from odoo.tests.in_memory_case import InMemoryCase

from .test_config_parameter import TestSetGetParam, TestTypedParams
from .test_form_create import (
    TestFormAttributeAccess,
    TestFormCreate,
    TestFormNestedX2many,
)
from .test_groups import (
    TestAllUsersCount,
    TestGroupsCacheInvalidation,
    TestGroupsOdoo,
    TestPrivilegeGroupSorting,
)
from .test_res_currency import TestResCurrency, TestResCurrencyRateMemoScope
from .test_res_lang import TestResLangUnsavedRecord, test_res_lang

# Each class below is a module's own test class, body untouched, run against
# an in-memory environment instead of the database (R3 in
# doc/architecture/risks.md). What a class needs beyond `base` it names in
# `hosts_modules`; what is genuinely database-bound -- hand-written SQL, a
# second cursor -- is skipped by name with the reason.

_RAW_SQL = "reads through hand-written SQL: database-bound by design"


class TestTypedParamsInMemory(InMemoryCase, TestTypedParams):
    pass


class TestSetGetParamInMemory(InMemoryCase, TestSetGetParam):
    def test_set_param_create_race(self):
        self.skipTest("opens a second cursor to race the INSERT: database-bound")


class TestGroupsOdooInMemory(InMemoryCase, TestGroupsOdoo):
    pass


class TestGroupsCacheInvalidationInMemory(InMemoryCase, TestGroupsCacheInvalidation):
    pass


class TestAllUsersCountInMemory(InMemoryCase, TestAllUsersCount):
    pass


class TestPrivilegeGroupSortingInMemory(InMemoryCase, TestPrivilegeGroupSorting):
    pass


class TestResCurrencyInMemory(InMemoryCase, TestResCurrency):
    def test_rate_memo_company_scoping_matches_sql(self):
        self.skipTest(_RAW_SQL)


class TestResCurrencyRateMemoScopeInMemory(InMemoryCase, TestResCurrencyRateMemoScope):
    def test_memo_matches_sql_for_every_access_context(self):
        self.skipTest(_RAW_SQL)

    def test_reference_paths_differ_by_access_context(self):
        self.skipTest(_RAW_SQL)


class TestResLangInMemory(InMemoryCase, test_res_lang):
    def test_lang_url_code_shortening(self):
        self.skipTest(_RAW_SQL)


class TestResLangUnsavedRecordInMemory(InMemoryCase, TestResLangUnsavedRecord):
    pass


class TestFormCreateInMemory(InMemoryCase, TestFormCreate):
    # a Form reads onchange(), which `web` implements
    hosts_modules = ("base", "web")


class TestFormNestedX2manyInMemory(InMemoryCase, TestFormNestedX2many):
    hosts_modules = ("base", "web")


class TestFormAttributeAccessInMemory(InMemoryCase, TestFormAttributeAccess):
    hosts_modules = ("base", "web")


class TestTheHostIsTheDbFreeTier(InMemoryCase):
    # what makes the classes above meaningful: they ran on the tier, not on
    # the database the odoo-bin run is otherwise using
    def test_the_environment_is_in_memory_and_carries_bases_data(self):
        from odoo.orm.model_test_env import InMemoryCursor

        self.assertIsInstance(self.env.cr, InMemoryCursor)
        self.assertEqual(self.env.cr.dbname, ":memory:")
        self.assertGreater(len(self.registry.models), 140)
        self.assertGreater(self.env["ir.access"].sudo().search_count([]), 150)
        self.assertEqual(self.env.ref("base.user_admin").login, "admin")

    def test_the_superuser_has_a_company_as_it_does_on_a_database(self):
        # an inactive user reached through res_company_users_rel: the relation
        # is a table to SQL, and a search over it does not filter the comodel
        self.assertEqual(self.env.companies.ids, [self.env.company.id])

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
