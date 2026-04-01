# -*- coding: utf-8 -*-

from odoo.tests import common


class TestPurchaseRequisitionCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseRequisitionCommon, cls).setUpClass()

        cls.env.user.group_ids += cls.env.ref('uom.group_uom')

        # Fetch purchase related user groups
        user_group_purchase_manager = cls.env.ref('purchase.group_purchase_manager')
        user_group_purchase_user = cls.env.ref('purchase.group_purchase_user')

        # User Data: purchase requisition Manager and User
        Users = cls.env['res.users'].with_context({'tracking_disable': True})

        cls.user_purchase_requisition_manager = Users.create({
            'name': 'Purchase requisition Manager',
            'login': 'prm',
            'email': 'requisition_manager@yourcompany.com',
            'notification_type': 'inbox',
            'group_ids': [(6, 0, [user_group_purchase_manager.id])]})

        cls.user_purchase_requisition_user = Users.create({
            'name': 'Purchase requisition User',
            'login': 'pru',
            'email': 'requisition_user@yourcompany.com',
            'notification_type': 'inbox',
            'group_ids': [(6, 0, [user_group_purchase_user.id])]})

        # Create Product
        cls.product_uom_id = cls.env.ref('uom.product_uom_unit')

        cls.product_09 = cls.env['product.product'].create({
            'name': 'Pedal Bin',
            'standard_price': 10.0,
            'list_price': 47.0,
            'type': 'consu',
            'uom_id': cls.product_uom_id.id,
            'default_code': 'E-COM10',
        })

        cls.product_13 = cls.env['product.product'].create({
            'name': 'Corner Desk Black',
            'standard_price': 78.0,
            'list_price': 85.0,
            'type': 'consu',
            'uom_id': cls.product_uom_id.id,
            'default_code': 'FURN_1118',
        })

        # In order to test process of the purchase requisition ,create requisition
        cls.bo_requisition = cls.env['purchase.requisition'].create({
            'line_ids': [(0, 0, {
                'product_id': cls.product_09.id,
                'product_qty': 10.0,
                'product_uom_id': cls.product_uom_id.id})]
        })

        cls.res_partner_1 = cls.env['res.partner'].create({
            'name': 'Wood Corner',
        })
