import openerp.exceptions
from openerp.tests.common import TransactionCase

class TestRules(TransactionCase):
    def setUp(self):
        super(TestRules, self).setUp()

        self.id1 = self.env['test_access_right.some_obj']\
            .create({'val': 1}).id
        self.id2 = self.env['test_access_right.some_obj']\
            .create({'val': -1}).id
        # create a global rule forbidding access to records with a negative
        # (or zero) val
        self.env['ir.rule'].create({
            'name': 'Forbid negatives',
            'model_id': self.browse_ref('test_access_rights.model_test_access_right_some_obj').id,
            'domain_force': "[('val', '>', 0)]"
        })

    def test_basic_access(self):
        env = self.env(user=self.browse_ref('base.public_user'))

        # put forbidden record in cache
        browse2 = env['test_access_right.some_obj'].browse(self.id2)
        # this is the one we want
        browse1 = env['test_access_right.some_obj'].browse(self.id1)

        # this should not blow up
        self.assertEqual(browse1.val, 1)

        # but this should
        with self.assertRaises(openerp.exceptions.AccessError):
            self.assertEqual(browse2.val, -1)
