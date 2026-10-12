# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.project_stock_account.tests.test_analytics import TestAnalytics


class TestAnalyticsReinvoice(TestAnalytics):

    def test_no_analytic_lines_for_reinvoicable_products(self):
        """ Delivering a product that is re-invoiced at cost should not charge the project.

        Under anglo-saxon accounting the cost of a re-invoiced product is already
        carried by the customer invoice, so validating a delivery from a picking
        linked to a project must leave the project's costs untouched, even when the
        operation type reports its costs on the project.
        """
        reinvoicable_product = self.env['product.product'].create({
            'name': 'product_order_cost',
            'standard_price': 100.0,
            'reinvoice_policy': 'cost',
        })
        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'project_id': self.project.id,
        })
        picking_out.picking_type_id.analytic_costs = True
        self.MoveObj.create({
            'uom_id': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': reinvoicable_product.id,
            'product_uom_qty': 3,
        })
        self.company.anglo_saxon_accounting = True
        picking_out.action_confirm()
        picking_out.with_user(self.user_stock_user).button_validate()

        self.assertFalse(
            picking_out.move_ids.analytic_account_line_ids,
            'There should not be any generated analytic lines as the product is reinvoicable and anglo-saxon accounting is enabled',
        )

    def test_analytic_lines_for_reinvoicable_products_other_active_company(self):
        """ Delivering a re-invoiced product should leave the project untouched even when
        the delivery is processed from another company.

        Only the products re-invoiced to the customer are left out, the rest of the
        delivery still charges the project.
        """
        other_company = self.env.ref('base.main_company')
        other_company.anglo_saxon_accounting = False
        self.company.anglo_saxon_accounting = True
        self.user_stock_user.company_ids |= other_company
        self.user_stock_user.company_id = other_company
        self.product1.reinvoice_policy = 'cost'
        self.picking_type_out.analytic_costs = True
        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'project_id': self.project.id,
            'move_ids': [
                Command.create({
                    'uom_id': self.uom_unit.id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'product_id': self.product1.id,
                    'product_uom_qty': 3,
                }),
                Command.create({
                    'uom_id': self.uom_unit.id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'product_id': self.product2.id,
                    'product_uom_qty': 5,
                }),
            ],
        })
        picking_out.action_confirm()
        picking_out.with_user(self.user_stock_user).with_company(other_company).button_validate()

        analytic_lines = picking_out.move_ids.analytic_account_line_ids
        self.assertEqual(analytic_lines.product_id, self.product2)
        self.assertEqual(analytic_lines.amount, -1000.0)
