# -*- coding: utf-8 -*-

from odoo.addons.l10n_mx_edi_extended.tests.common import TestMxExtendedEdiCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo import fields
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiResults(TestMxExtendedEdiCommon, ValuationReconciliationTestCommon):

    def create_sale_order(self):
        return self.obj_sale.create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, ope) for ope in [{
                'name': p.name, 'product_id': p.id, 'product_uom_qty': 2,
                'product_uom': p.uom_id.id, 'price_unit': p.list_price,
                'tax_id': [(4, self.tax_positive.id)],
            } for (_, p) in self.products.items()]],
        })

    def test_invoice_cfdi_landing(self):
        self.env.user.groups_id |= self.env.ref('purchase.group_purchase_manager')
        self.env.user.groups_id |= self.env.ref('stock.group_stock_manager')
        self.env.user.groups_id |= self.env.ref('sales_team.group_sale_manager')

        inventory_user = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Inventory user',
            'login': 'sliwa',
            'email': 'queen@goth.mx',
            'groups_id': [(6, 0, [self.env.ref('stock.group_stock_user').id])]
        })

        with freeze_time(self.frozen_today):
            self.product.write({
                'categ_id': self.stock_account_product_categ.id,
                'type': 'product',
                'landed_cost_ok': True,
                'invoice_policy': 'delivery',
            })

            purchase = self.env['purchase.order'].create({
                'partner_id': self.partner_a.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_qty': 2,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': self.product.list_price,
                        'taxes_id': [(6, 0, self.product.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.env.company)).ids)],
                        'date_planned': fields.Datetime.now(),
                    })
                ],
            })

            purchase.button_confirm()
            picking_purchase = purchase.picking_ids
            picking_purchase.move_line_ids.write({'quantity': 2})
            picking_purchase.button_validate()

            landing_cost = self.env['stock.landed.cost'].create({
                'l10n_mx_edi_customs_number': '15  48  3009  0001234',
                'picking_ids': [(4, picking_purchase.id)],
                'cost_lines': [(0, 0, {
                    'product_id': self.product.id,
                    'price_unit': 100,
                    'split_method': 'by_quantity',
                    'account_id': self.company_data['default_account_assets'].id,
                })],
                'account_journal_id': self.company_data['default_journal_misc'].id,
            })
            landing_cost.compute_landed_cost()
            landing_cost.button_validate()

            sale = self.env['sale.order'].create({
                'partner_id': self.partner_a.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product.name,
                        'product_id': self.product.id,
                        'product_uom_qty': 2,
                        'product_uom': self.product.uom_id.id,
                        'price_unit': self.product.list_price,
                        'tax_id': [(6, 0, self.product.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.env.company)).ids)],
                    })
                ],
            })

            sale.action_confirm()
            picking_sale = sale.picking_ids

            # Generate two moves for procurement by partial delivery
            picking_sale.action_assign()
            picking_sale.move_line_ids.write({'quantity': 1})
            res_dict = picking_sale.button_validate()
            self.env[res_dict['res_model']]\
                .with_context(res_dict['context'])\
                .with_user(inventory_user)\
                .process()

            picking_backorder = sale.picking_ids.filtered(lambda r: r.state == 'assigned')
            picking_backorder.move_line_ids.write({'quantity': 1})
            picking_backorder.button_validate()

            invoice = sale._create_invoices()
            invoice.action_post()

            self.assertRecordValues(invoice.invoice_line_ids, [{
                'l10n_mx_edi_customs_number': landing_cost.l10n_mx_edi_customs_number,
            }])
