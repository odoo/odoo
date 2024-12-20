# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class UomCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.uom_gram = cls.env.ref('uom.product_uom_gram')
        cls.uom_kgm = cls.env.ref('uom.product_uom_kgm')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_pack_of_6 = cls.env.ref('uom.product_uom_pack_6')

        cls.group_uom = cls.env.ref('uom.group_uom')

    @classmethod
    def _enable_uom(cls):
        cls.env.user.groups_id += cls.group_uom

    @classmethod
    def _disable_uom(cls):
        cls.env.user.groups_id -= cls.group_uom
