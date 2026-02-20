from odoo.tests.common import tagged, TransactionCase
from unittest.mock import patch


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestTransactionEnvs(TransactionCase):
    def test_transation_envs_weakrefs(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        base_x = self.env['base'].with_context(test_stuff=False)
        base_x_env_id = id(base_x.env)
        self.assertIn(base_x.env, transaction.envs)
        del base_x

        base_x = self.env['base'].with_context(test_stuff=False)
        self.assertEqual(id(base_x.env), base_x_env_id, "We should get the same environment")
        del base_x

        transaction.reset()
        self.assertEqual(set(transaction.envs), starting_envs)

    def test_transaction_envs_many(self):
        model = self.env['base']
        counts = []
        combinations = [(a, b) for a in range(100, 200) for b in range(200, 300)]
        with patch.object(model.env.transaction.__class__, 'compactify_envs', side_effect=model.env.transaction.compactify_envs) as deref_func:
            for ctx_val, uid in combinations:
                # getting 2 environments per loop
                model.with_user(uid).with_context(val=ctx_val)
                env_count = sum(1 for _ in model.env.transaction.envs)
                counts.append(env_count)
                self.assertLess(env_count, 100, f"Make sure we never allocate too many environments at once: ...{counts[-10:]} at val={ctx_val}, uid={uid}")
            deref_func.assert_called()
            self.assertLess(deref_func.call_count / len(combinations), 0.1, "Cleaning too much")
            self.assertGreater(max(counts), 30, "The test did not stress enough allocations (check key) or wrong assumptions")

    def do_stuff_with_env(self):
        base_test = self.env['base'].with_context(test_stuff=False)
        base_test |= self.env['base'].with_context(test_stuff=1)
        base_test |= self.env['base'].with_context(test_stuff=2)
        return base_test

    def test_transation_envs_weakrefs_call(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        self.do_stuff_with_env()
        transaction.reset()
        self.assertEqual(set(transaction.envs), starting_envs)

    def test_transation_envs_weakrefs_return(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        base_test = self.do_stuff_with_env()
        transaction.reset()
        self.assertEqual(set(transaction.envs), starting_envs | {base_test.env})

    def test_transation_envs_ordered(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        # create environments in a certain order, not sorted on item
        items = [3, 8, 1, 5, 2, 7, 6, 9, 0, 4]
        envs = [self.env(context={'item': item}) for item in items]
        # check that those environments appear in order in transaction.envs
        env_items = [env.context['item'] for env in transaction.envs if env not in starting_envs]
        self.assertEqual(env_items, items)
        del envs
        transaction.reset()
        self.assertEqual(set(transaction.envs), starting_envs)
