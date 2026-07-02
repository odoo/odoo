import odoo.models
from odoo import Command

from odoo.addons.base.tests.common import BaseCommon


class TestOrmPartnerCommon(BaseCommon):
    @classmethod
    def _load_partners_set(cls):
        cls.partner_category = cls.env['test_orm.partner.category'].create({'name': 'Sellers'})
        cls.country_be = cls.env['test_orm.country'].create({'name': 'Belgium'})
        cls.partners = cls.env['test_orm.partner'].create([
            {
                'name': 'Inner Works',
                'category_id': cls.partner_category,
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Alabama'}).id,
                'child_ids': [
                    Command.create({'name': 'Sheila Ruiz'}),
                    Command.create({'name': 'Wyatt Howard'}),
                    Command.create({'name': 'Austin Kennedy'}),
                ],
            }, {
                'name': 'Pepper Street',
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Alaska'}).id,
                'child_ids': [
                    Command.create({'name': 'Liam King'}),
                    Command.create({'name': 'Craig Richardson'}),
                    Command.create({'name': 'Adam Cox'}),
                ],
            }, {
                'name': 'AnalytIQ',
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Arizona'}).id,
                'child_ids': [
                    Command.create({'name': 'Pedro Boyd'}),
                    Command.create({'name': 'Landon Roberts'}),
                    Command.create({'name': 'Leona Shelton'}),
                    Command.create({'name': 'Scott Kim'}),
                ],
            }, {
                'name': 'Urban Trends',
                'category_id': cls.partner_category,
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Arkansas'}).id,
                'child_ids': [
                    Command.create({'name': 'Louella Jacobs'}),
                    Command.create({'name': 'Albert Alexander'}),
                    Command.create({'name': 'Brad Castillo'}),
                    Command.create({'name': 'Sophie Montgomery'}),
                    Command.create({'name': 'Chloe Bates'}),
                    Command.create({'name': 'Mason Crawford'}),
                    Command.create({'name': 'Elsie Kennedy'}),
                ],
            }, {
                'name': 'Ctrl-Alt-Fix',
                'state_id': cls.env['test_orm.country.state'].create({'name': 'California'}).id,
                'child_ids': [
                    Command.create({'name': 'Carole Miller'}),
                    Command.create({'name': 'Cecil Holmes'}),
                ],
            }, {
                'name': 'Ignitive Labs',
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Colorado'}).id,
                'child_ids': [
                    Command.create({'name': 'Jonathan Webb'}),
                    Command.create({'name': 'Clinton Clark'}),
                    Command.create({'name': 'Howard Bryant'}),
                ],
            }, {
                'name': 'Amber & Forge',
                'state_id': cls.env['test_orm.country.state'].create({'name': 'Connecticut'}).id,
                'child_ids': [
                    Command.create({'name': 'Mark Webb'}),
                ],
            }, {
                'name': 'Rebecca Day',
                'parent_id': cls.env['test_orm.partner'].create({
                    'name': 'Leslie Wilson',
                    'state_id': cls.env['test_orm.country.state'].create({'name': 'Delaware'}).id,
                }).id,
            }, {
                'name': 'Gabriella Jennings',
                'parent_id': cls.env['test_orm.partner'].create({'name': 'Jeanne Sanchez'}).id,
            }
        ])

    def assertIsRecordset(self, value, model):
        self.assertIsInstance(value, odoo.models.BaseModel)
        self.assertEqual(value._name, model)

    def assertIsRecord(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertTrue(len(value) <= 1)

    def assertIsEmptyRecordset(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertFalse(value)
