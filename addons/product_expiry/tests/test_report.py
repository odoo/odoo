# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestReports(TestReportsCommon):

    def test_reports_expiry(self):
        lot1 = self.env['stock.production.lot'].create({
            'name': 'Volume-Beta"',
            'product_id': self.product1.id,
            'company_id': self.env.company.id,
            'use_date': "2024-03-20 13:30:06",
            'use_expiration_date': True,
            'expiration_date': "2024-03-21 13:30:06",
        })
        report = self.env.ref('stock.label_lot_template')
        target = b'\n\n^XA\n^FO100,50\n^A0N,44,33^FD[C4181234""154654654654]Mellohi"^FS\n^FO100,100\n^A0N,44,33^FDLN/SN:Volume-Beta\"^FS\n\n^FO100,150\n^A0N,44,33^FDBestbefore:03/20/2024^FS\n\n^FO100,200\n^A0N,44,33^FDUseby:03/21/2024^FS\n^FO100,250^BY3\n^BCN,100,Y,N,N\n^FDVolume-Beta\"^FS\n\n\n^XZ\n\n'
        rendering, qweb_type = report._render_qweb_text(lot1.id)
        self.assertEqual(target, rendering.replace(b' ', b''), 'The rendering is not good')
        self.assertEqual(qweb_type, 'text', 'the report type is not good')
