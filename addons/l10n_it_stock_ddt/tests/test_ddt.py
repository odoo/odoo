# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged, Form


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDDT(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_it.l10n_it_chart_template_generic'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
                        'vat':"IT12345670017",
                        'country_id': cls.env.ref('base.it').id,
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
        if hasattr(settings, 'button_create_proxy_user'):
            # Needed when `l10n_it_edi_sdiscoop` is installed
            settings.button_create_proxy_user()


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
                                   'product_uom': p.uom_id.id,
                                   'price_unit': p.list_price,
                                   'tax_id': self.company_data['default_tax_sale']})
                           for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # deliver partially
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        self.assertTrue(pick.l10n_it_ddt_number, 'The outgoing picking should have a DDT number')
        self.inv1 = self.so._create_invoices()
        self.inv1.action_post()
        self.assertEqual(self.inv1.l10n_it_ddt_ids.ids, pick.ids, 'DDT should be linked to the invoice')

        # deliver partially
        pickx1 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx1.move_ids.write({'quantity_done': 1})
        wiz_act = pickx1.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # and again
        pickx2 = self.so.picking_ids.filtered(lambda p: p.state != 'done')
        pickx2.move_ids.write({'quantity_done': 2})
        wiz_act = pickx2.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        self.inv2 = self.so._create_invoices()
        self.inv2.action_post()
        self.assertEqual(self.inv2.l10n_it_ddt_ids.ids, (pickx1 | pickx2).ids, 'DDTs should be linked to the invoice')

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
                                   'product_uom': self.product_a.uom_id.id,
                                   'price_unit': self.product_a.list_price,
                                   'tax_id': self.company_data['default_tax_sale']
                                   }
                            )],
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
        })
        so.action_confirm()

        # deliver partially
        picking_1 = so.picking_ids
        picking_1.move_ids.write({'quantity_done': 1})
        wiz_act = picking_1.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        invoice_1 = so._create_invoices()
        invoice_form = Form(invoice_1)
        with invoice_form.invoice_line_ids.edit(0) as line:
            line.quantity = 1.0
        invoice_1 = invoice_form.save()
        invoice_1.action_post()

        picking_2 = so.picking_ids.filtered(lambda p: p.state != 'done')
        picking_2.move_ids.write({'quantity_done': 2})
        picking_2.button_validate()

        invoice_2 = so._create_invoices()
        invoice_2.action_post()

        # Invalidate the cache to ensure the lines will be fetched in the right order.
        picking_2.invalidate_cache()
        self.assertEqual(invoice_1.l10n_it_ddt_ids.ids, picking_1.ids, 'DDT picking_1 should be linked to the invoice_1')
        self.assertEqual(invoice_2.l10n_it_ddt_ids.ids, picking_2.ids, 'DDT picking_2 should be linked to the invoice_2')
