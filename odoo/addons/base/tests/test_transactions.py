from odoo.tests.common import TransactionCase


class TestTransactionEnvs(TransactionCase):
    def test_transation_envs_weakrefs(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        base_x = self.env['base'].with_context(test_stuff=False)
        self.assertIn(base_x.env, transaction.envs)
        del base_x
        self.assertEqual(set(transaction.envs), starting_envs)

    def do_stuff_with_env(self):
        base_test = self.env['base'].with_context(test_stuff=False)
        base_test |= self.env['base'].with_context(test_stuff=1)
        base_test |= self.env['base'].with_context(test_stuff=2)
        return base_test

    def test_transation_envs_weakrefs_call(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        self.do_stuff_with_env()
        self.assertEqual(set(transaction.envs), starting_envs)

    def test_transation_envs_weakrefs_return(self):
        transaction = self.env.transaction
        starting_envs = set(transaction.envs)
        base_test = self.do_stuff_with_env()
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
        self.assertEqual(set(transaction.envs), starting_envs)
