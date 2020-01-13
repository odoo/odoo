# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
import odoo.tests


class TestReports(odoo.tests.TransactionCase):
    def setUp(cls):
        super(TestReports, cls).setUp()
        user_group_stock_user = cls.env.ref('stock.group_stock_user')
        user_group_stock_manager = cls.env.ref('stock.group_stock_manager')

        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_stock_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_user.id])]})
        cls.user_stock_manager = Users.create({
            'name': 'Julie Tablier',
            'login': 'julie',
            'email': 'j.j@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_manager.id])]})
        cls.env = cls.env(user=cls.user_stock_user)

    def test_reports(self):
        product1 = self.env['product.product'].with_user(self.user_stock_manager).create({
            'name': 'Mellohi',
            'default_code': 'C418',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot',
            'barcode': 'scan_me'
        })
        lot1 = self.env['stock.production.lot'].create({
            'name': 'Volume-Beta',
            'product_id': product1.id,
            'company_id': self.env.company.id,
        })
        report = self.env.ref('stock.label_lot_template')
        target = b'\n\n\n^XA\n^FO100,50\n^A0N,44,33^FD[C418]Mellohi^FS\n^FO100,100\n^A0N,44,33^FDLN/SN:Volume-Beta^FS\n^FO100,150^BY3\n^BCN,100,Y,N,N\n^FDVolume-Beta^FS\n^XZ\n\n\n'

        rendering, qweb_type = report.render_qweb_text(lot1.id)
        self.assertEqual(target, rendering.replace(b' ', b''), 'The rendering is not good')
        self.assertEqual(qweb_type, 'text', 'the report type is not good')
