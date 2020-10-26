from odoo.tests.common import TransactionCase

class TestNoDefaultPropagation(TransactionCase):
    def test_sub_create(self):
        """ `default_{name}` keys should not be propagated to the creation of
        sub-records
        """
        Model = self.env['test_new_api.model_parent_m2o'].with_context(default_name="STAFF SGT. MAX FUCKING FIGHTMASTER")

        rec = Model.create({
            'child_ids': [(0, 0, {})]
        })
        self.assertEqual(rec.name, "STAFF SGT. MAX FUCKING FIGHTMASTER")
        self.assertEqual(rec.child_ids.name, False)

    def test_subsequent(self):
        """ `default_{name}` should not be set on the resulting record
        """
        Model = self.env['test_new_api.model_parent_m2o'].with_context(default_name="Richard Pound")

        r1 = Model.create({})
        r2 = r1.create({})
        self.assertEqual(r1.name, "Richard Pound")
        self.assertEqual(r2.name, False)

    def test_sub_create_weird(self):
        """ If the field with a default is a related then nothing should happen,
        and the field should still get stripped.
        """

        Model = self.env['test_new_api.multi'].with_context(default_name="Dr. Steel")

        rec = Model.create({'lines': [(0, 0, {})]})
        self.assertFalse(rec.partner)
        self.assertEqual(rec.name, False)
        self.assertEqual(rec.lines.name, False)

    def test_sub_inherits(self):
        """ If the field is *inherited* however... probably it should go through?
        """
        Model = self.env['test_new_api.inherit.simple'].with_context(default_name="Dr. Steel")

        rec = Model.create({})
        self.assertNotEqual(rec.country_id, False)
        self.assertEqual(rec.name, 'Dr. Steel')
