# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import tagged, Form
from unittest.mock import patch
from odoo.addons.account.models.account_move_line import AccountMoveLine
from odoo.addons.stock_account.models.account_move import AccountMove
from odoo.addons.stock_account.models.stock_move import StockMove


@tagged("post_install", "-at_install")
class ValuationReconciliationTest(ValuationReconciliationTestCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.test_product_delivery_2 = cls.env['product.product'].create({
            'name': 'Test product template invoiced on delivery 2',
            'standard_price': 42.0,
            'type': 'product',
            'categ_id': cls.stock_account_product_categ.id,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

    def test_anglo_saxon_valuation_reconciliation(self):
        """In some particular cases, _stock_account_anglo_saxon_reconcile_valuation tries to reconcile the same account_move_line twice.
        This test checks if there is a step in the method that prevents this.
        """
        self.env.company.anglo_saxon_accounting = True

        products = [self.test_product_delivery, self.test_product_delivery_2]

        # Create invoices
        invoices = []
        for product in products:
            move_form = Form(self.env["account.move"].with_context(default_move_type="out_invoice"))
            move_form.partner_id = self.partner_a
            move_form.currency_id = self.currency_data["currency"]
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
            invoices.append(move_form.save())

        # Creating the aml that would be reconciled twice if no reconciliation checking step is implemented
        broken_aml = self.env['account.move.line'].create({
            'name': "broken aml",
            'product_id': self.test_product_delivery.id,
            'account_id': self.stock_account_product_categ["property_stock_account_output_categ_id"].id,
            'move_id': invoices[0].id
        })

        # Creating dummy stock.move to bypass other check
        stock_location = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1).lot_stock_id

        product = products[0]

        out_picking = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': stock_location.warehouse_id.out_type_id.id,
        })

        sm = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'location_id': out_picking.location_id.id,
            'location_dest_id': out_picking.location_dest_id.id,
            'picking_id': out_picking.id,
        })

        # Patched methods to bypass other checks
        def _stock_account_get_last_step_stock_moves(self):
            return sm

        def _reconcile_plan(self, reconciliation_plan):
            for amls in reconciliation_plan:
                for aml in amls:
                    if aml.reconciled:
                        raise AssertionError("Journal items should not be reconciled twice")
                    aml.reconciled = True

        def _get_all_related_sm(self, prod):
            return self

        def _get_all_related_aml(self):
            return broken_aml

        # Running _post with patched methods (which calls _stock_account_anglo_saxon_reconcile_valuation)
        with (
            patch.object(AccountMoveLine, '_reconcile_plan', _reconcile_plan),
            patch.object(AccountMove, '_stock_account_get_last_step_stock_moves', _stock_account_get_last_step_stock_moves),
            patch.object(StockMove, '_get_all_related_sm', _get_all_related_sm),
            patch.object(StockMove, '_get_all_related_aml', _get_all_related_aml),
        ):

            # Creating an svl associated to one invoice to populate the no_exchange_reconcile_plan
            svl_vals = {
                'company_id': self.env.company.id,
                'product_id': product.id,
                'description': "description",
                'value': 0,
                'quantity': 0,
            }

            invoices[1].stock_valuation_layer_ids |= self.env['stock.valuation.layer'].create(svl_vals)
            invoices[1].stock_valuation_layer_ids.stock_valuation_layer_id |= self.env['stock.valuation.layer'].create(svl_vals)

            invoice = invoices[0] | invoices[1]

            invoice._post()
