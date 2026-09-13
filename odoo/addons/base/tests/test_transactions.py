from odoo.orm.runtime.transaction import RECENT_ENVIRONMENTS
from odoo.tests.common import TransactionCase


class TestTransactionEnvs(TransactionCase):
    def _live_envs(self):
        return {env for env in self.env.transaction.envs if "_flood" not in env.context}

    def _evict_recent_envs(self):
        for n in range(RECENT_ENVIRONMENTS):
            self.env(context={"_flood": n})

    def test_transation_envs_weakrefs(self):
        starting_envs = self._live_envs()
        base_x = self.env["base"].with_context(test_stuff=False)
        base_env = base_x.env
        self.assertIn(base_env, self._live_envs())
        del base_x
        # a dropped environment stays for RECENT_ENVIRONMENTS constructions
        self.assertEqual(self._live_envs(), starting_envs | {base_env})
        del base_env
        self._evict_recent_envs()
        self.assertEqual(self._live_envs(), starting_envs)

    def do_stuff_with_env(self):
        base_test = self.env["base"].with_context(test_stuff=False)
        base_test |= self.env["base"].with_context(test_stuff=1)
        base_test |= self.env["base"].with_context(test_stuff=2)
        return base_test

    def test_transation_envs_weakrefs_call(self):
        starting_envs = self._live_envs()
        self.do_stuff_with_env()
        self._evict_recent_envs()
        self.assertEqual(self._live_envs(), starting_envs)

    def test_transation_envs_weakrefs_return(self):
        starting_envs = self._live_envs()
        base_test = self.do_stuff_with_env()
        self._evict_recent_envs()
        self.assertEqual(self._live_envs(), starting_envs | {base_test.env})

    def test_transation_envs_ordered(self):
        transaction = self.env.transaction
        starting_envs = self._live_envs()
        items = [3, 8, 1, 5, 2, 7, 6, 9, 0, 4]
        envs = [self.env(context={"item": item}) for item in items]
        env_items = [
            env.context["item"] for env in transaction.envs if env not in starting_envs
        ]
        self.assertEqual(env_items, items)
        del envs
        self._evict_recent_envs()
        self.assertEqual(self._live_envs(), starting_envs)
