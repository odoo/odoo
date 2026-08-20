# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.base.tests.common import BaseCommon


class UomCommon(BaseCommon):
    _test_user_groups = ('base.group_user',)

    _test_user_name = 'Test User'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.uom_gram = cls.quick_ref('uom.product_uom_gram')
        cls.uom_kgm = cls.quick_ref('uom.product_uom_kgm')
        cls.uom_ton = cls.quick_ref('uom.product_uom_ton')
        cls.uom_unit = cls.quick_ref('uom.product_uom_unit')
        cls.uom_dozen = cls.quick_ref('uom.product_uom_dozen')
        cls.uom_dozen.active = True
        cls.uom_hour = cls.quick_ref('uom.product_uom_hour')
        cls.uom_pack_6 = cls.quick_ref('uom.product_uom_pack_6')

        cls.group_uom = cls.quick_ref('uom.group_uom')

    @classmethod
    def _enable_uom(cls):
<<<<<<< 423770de9c5da4ca862e9e972c0caf8fa3f1a886
        cls.group_user._apply_group(cls.group_uom)
||||||| cd826c81964566d831d200059e62bb7dfe88d088
        cls.env.user.group_ids += cls.group_uom
=======
        cls.env.ref('base.group_user').write({'implied_ids': [
            Command.link(cls.group_uom.id),
        ]})
>>>>>>> b21be1b717fb6c929961e09cfd18e3c3545124d4

    @classmethod
    def _disable_uom(cls):
<<<<<<< 423770de9c5da4ca862e9e972c0caf8fa3f1a886
        cls.group_user._remove_group(cls.group_uom)
||||||| cd826c81964566d831d200059e62bb7dfe88d088
        cls.env.user.group_ids -= cls.group_uom
=======
        cls.env.ref('base.group_user').write({'implied_ids': [
            Command.unlink(cls.group_uom.id),
        ]})
>>>>>>> b21be1b717fb6c929961e09cfd18e3c3545124d4
