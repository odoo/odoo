# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import BaseCommon


class UomCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.uom_gram = cls.quick_ref('uom.product_uom_gram')
        cls.uom_kgm = cls.quick_ref('uom.product_uom_kgm')
        cls.uom_ton = cls.quick_ref('uom.product_uom_ton')
        cls.uom_unit = cls.quick_ref('uom.product_uom_unit')
        cls.uom_dozen = cls.quick_ref('uom.product_uom_dozen')
        cls.uom_hour = cls.quick_ref('uom.product_uom_hour')

        cls.group_uom = cls.quick_ref('uom.group_uom')

    @classmethod
    def _enable_uom(cls):
        cls.env.user.groups_id += cls.group_uom

    @classmethod
    def _disable_uom(cls):
        cls.env.user.groups_id -= cls.group_uom
