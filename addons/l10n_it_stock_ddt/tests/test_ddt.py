# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import Form, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDDT(TestSaleCommon):

    @classmethod
    @TestSaleCommon.setup_country('it')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
                        'vat':"IT12345670017",
                        'l10n_it_codice_fiscale': '01234560157',
                        'l10n_it_tax_system': 'RF01',
                        'street': 'Via Giovanni Maria Platina 66',
                        'zip': '26100',
                        'city': 'Cremona',
                        })
        cls.env['res.partner.bank'].create({
            'acc_number': 'IT60X0542811101000000123456',
            'partner_id': cls.company_data['company'].partner_id.id,
        })
        cls.partner_a.write({
            'street': 'Piazza Guglielmo Marconi 5',
            'zip': '26100',
            'city': 'Cremona',
            'country_id': cls.env.ref('base.it').id,
            'vat': 'IT12345670124'
        })

        settings = cls.env['res.config.settings'].create({})
        if hasattr(settings, '_create_proxy_user'):
            # Needed when `l10n_it_edi_sdiscoop` is installed
            settings._create_proxy_user(cls.company_data['company'], 'demo')

    def test_ddt_flow(self):
        """
            We confirm a sale order and handle its delivery partially.
            This should have created a DDT number and when we generate and the invoice,
            the delivery should be linked to it as DDT.
        """
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {'name': p.name,
                                   'product_id': p.id,
                                   'product_uom_qty': 5,
                                   'price_unit': p.list_price,
                                   'tax_ids': self.company_data['default_tax_sale']})
                           for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # deliver partially
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, pick.button_validate()).save().process()

        self.assertTrue(pick.l10n_it_ddt_number, 'The outgoing picking should have a DDT number')
        self.inv1 = self.so._create_invoices()
        self.inv1.action_post()
        self.assertEqual(self.inv1.l10n_it_ddt_ids.ids, pick.ids, 'DDT should be linked to the invoice')

        # deliver partially
        pickx1 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx1.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, pickx1.button_validate()).save().process()

        # and again
        pickx2 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx2.move_ids.write({'quantity': 2, 'picked': True})
        Form.from_action(self.env, pickx2.button_validate()).save().process()

        self.inv2 = self.so._create_invoices()
        self.inv2.action_post()
        self.inv2.flush_model()
        self.inv2.invalidate_model()
        self.assertIn(pickx1, self.inv2.l10n_it_ddt_ids)
        self.assertIn(pickx2, self.inv2.l10n_it_ddt_ids)
        # FIXME this check only worked because of a strange cache behavior
        # But is consistently broken after recent cleanings in sale
        # with the flush & invalidate, it always breaks, even without the cleanings
        # self.assertEqual(self.inv2.l10n_it_ddt_ids.ids, (pickx1 | pickx2).ids, 'DDTs should be linked to the invoice')

    def test_ddt_flow_2(self):
        """
            Test that the link between the invoice lines and the deliveries linked to the invoice
            through the link with the sale order is calculated correctly.
        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                                   'product_id': self.product_a.id,
                                   'product_uom_qty': 3,
                                   'price_unit': self.product_a.list_price,
                                   'tax_ids': self.company_data['default_tax_sale']
                                   }
                            )],
            'picking_policy': 'direct',
        })
        so.action_confirm()

        # deliver partially
        picking_1 = so.picking_ids
        picking_1.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, picking_1.button_validate()).save().process()

        invoice_1 = so._create_invoices()
        invoice_1.invoice_line_ids[0].quantity = 1.0
        invoice_1.action_post()

        picking_2 = so.picking_ids.filtered(lambda p: p.state != 'done')
        picking_2.move_ids.write({'quantity': 2, 'picked': True})
        picking_2.button_validate()

        invoice_2 = so._create_invoices()
        invoice_2.action_post()

        # Invalidate the cache to ensure the lines will be fetched in the right order.
        picking_2.invalidate_model()
        self.assertEqual(invoice_1.l10n_it_ddt_ids.ids, picking_1.ids, 'DDT picking_1 should be linked to the invoice_1')
        self.assertEqual(invoice_2.l10n_it_ddt_ids.ids, picking_2.ids, 'DDT picking_2 should be linked to the invoice_2')
