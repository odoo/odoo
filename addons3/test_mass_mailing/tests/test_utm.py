# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests import common
from odoo.tests import tagged, users


@tagged("utm")
class TestUTM(common.TestMassMailCommon):

    @users("employee")
    def test_utm_source_mixin_name(self):
        """ Test name management with source mixin, as name should be unique
        and automatically incremented """
        sources = self.env["utm.test.source.mixin"].create([
            {
                'name': 'Test',
                'title': 'Test',
            }
            for idx in range(5)]
        )
        self.assertListEqual(
            sources.mapped('name'),
            ["Test", "Test [2]", "Test [3]", "Test [4]", "Test [5]"]
        )

    @users("employee")
    def test_utm_source_mixin_name_brackets(self):
        """ Test with brackets """
        false_dupes = self.env["utm.test.source.mixin"].create([
            {
                'name': 'NewTest [2]',
                'title': 'NewTest',
            }
            for idx in range(3)] + [
            {
                'name': 'NewTest [3]',
                'title': 'NewTest',
            }, {
                'name': 'NewTest',
                'title': 'NewTest',
            }]
        )
        self.assertListEqual(
            false_dupes.mapped('name'),
            ["NewTest [2]", "NewTest", "NewTest [3]", "NewTest [4]", "NewTest [5]"]
        )

        new_source = self.env["utm.test.source.mixin"].create({
            "name": "OtherTest [2]",
        })
        self.assertEqual(new_source.name, "OtherTest [2]")

    @users("employee")
    def test_utm_source_mixin_name_cross_model(self):
        """ Uniqueness of source should be ensured cross models. For this purpose
        we use two models using the utm.source.mixin, allowing to check conflict
        management between models. """
        source_1 = self.env["utm.test.source.mixin"].create({
            "name": "Test",
            "title": "Test",
        })
        self.assertEqual(source_1.name, "Test")
        self.assertEqual(source_1.title, "Test")

        source_other_1 = self.env["utm.test.source.mixin.other"].create({
            "name": "Test",
            "title": "Test",
        })
        self.assertEqual(source_other_1.name, "Test [2]")
        self.assertEqual(source_other_1.title, "Test")

        source_other_2 = self.env["utm.test.source.mixin.other"].create({
            "name": "New",
            "title": "New",
        })
        self.assertEqual(source_other_2.name, "New")
        self.assertEqual(source_other_2.title, "New")

        source_other_2.write({"name": "Test"})
        self.assertEqual(source_other_2.name, "Test [3]")
        self.assertEqual(source_other_2.title, "New")

        source_2 = source_1.copy()
        self.assertEqual(source_2.name, "Test [4]")
        self.assertEqual(source_2.title, "Test")
