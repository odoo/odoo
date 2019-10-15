# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


class TestMonetaryAccess(odoo.tests.HttpCase):

    def test_monetary_access_create(self):
        """Monetary fields that depend on compute/related currency
           have never really been supported by the ORM.
           However most currency fields are related.
           This limitation can cause monetary fields to not be rounded,
           as well as trigger spurious ACL errors.
        """
        user_admin = self.env.ref("base.user_admin")
        user_demo = self.env.ref("base.user_demo").with_user(user_admin)

        # this would raise without the fix introduced in this commit
        new_user = user_demo.copy({'monetary': 1/3})

        # The following is here to document how the ORM behaves, not really part of the test;
        # in particular these specific points highlight the discrepancy between what is sent
        # to the database and what we get on the ORM side.
        # (to be fair, these are pre-existing ORM limitations that should have been avoided
        # by using more careful field definitions and testing)
        self.assertEqual(new_user.currency_id.id, False,
                         "The cache contains the wrong value for currency.")
        self.assertEqual(new_user.monetary, 1/3,
                         "Because of previous point, no rounding was done.")

        new_user.invalidate_cache()

        self.assertEqual(new_user.currency_id.rounding, 0.01,
                         "We now get the correct currency.")
        self.assertEqual(new_user.monetary, 0.33,
                         "The value was rounded when added to the cache.")
