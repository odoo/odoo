# coding: utf-8
from odoo.tests.common import TransactionCase


class TestPartnerMerge(TransactionCase):
    def setUp(self):
        super(TestPartnerMerge, self).setUp()
        self.partner1 = self.env.ref('base.res_partner_4')
        self.partner2 = self.env.ref('base.res_partner_4').copy()
        self.user = self.env.ref('base.user_demo')

    def _do_merge(self):
        # Switch to old API due to guessing mismatch
        wizard_obj = self.env['base.partner.merge.automatic.wizard']
        wizard_obj._merge((self.partner1 + self.partner2).ids, self.partner2)

    def test_partner_merge(self):
        self._do_merge()

    def test_partner_merge_protected_field(self):
        """ Protecting a field with a specific group does not break merging """
        column = self.env['res.partner']._fields['credit_limit']
        groups_orig = getattr(column, 'groups', None)
        column.groups = 'base.group_system'
        try:
            self._do_merge()
        finally:
            column.groups = groups_orig
