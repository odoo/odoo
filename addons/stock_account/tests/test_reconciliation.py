from openerp.tests.common import TransactionCase
from openerp.tools import float_round


class TestCostJournal(TransactionCase):
    """

    """

    def setUp(self):
        super(TestCostJournal, self).setUp()
        self.picking = self.registry('stock.picking')
        self.data = self.registry("ir.model.data")
        self.stock_move = self.registry('stock.move')
        self.invoice = self.registry('account.invoice')
        self.decimal = self.registry('decimal.precision')
        self.move_line = self.registry('account.move.line')
        self.stock_invoice = self.registry('stock.invoice.onshipping')
        self.tran_detail = self.registry('stock.transfer_details')
        # Set the values to use in the test
        self.partner_id = self.data.\
            get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.pick_type = self.data.\
            get_object_reference(self.cr, self.uid, "stock",
                                 "picking_type_out")[1]
        self.loc_id = self.data.\
            get_object_reference(self.cr, self.uid, "stock",
                                 "stock_location_stock")[1]
        self.loc_dest_id = self.data.\
            get_object_reference(self.cr, self.uid, "stock",
                                 "stock_location_customers")[1]
        acc_out_id = self.data.\
            get_object_reference(self.cr, self.uid, "account",
                                 "o_income")[1]
        acc_in_id = self.data.\
            get_object_reference(self.cr, self.uid, "account",
                                 "o_expense")[1]
        self.product_id = self.data.\
            get_object(self.cr, self.uid, "product",
                       "product_product_4")
        # Configure the product to generate journal from picking
        # Set a special cost to test the rounding
        self.product_id.write({'standard_price': 84.4628,
                               'valuation': 'real_time',
                               'cost_method': 'standard'})
        # Set required accounts in the category
        self.product_id.categ_id.write({
            'property_stock_account_input_categ': acc_in_id,
            'property_stock_account_output_categ': acc_out_id,
            })

    def test_CostJournal(self):
        '''
        Test the total in the credit and debit amount from
        account move line created from a picking with a product
        with Real Time valuation
        '''
        cr, uid = self.cr, self.uid
        # Creating picking out with a product with real time valuation
        pick_id = self.picking.\
            create(cr, uid,
                   {
                       'picking_type_id': self.pick_type,
                       'partner_id': self.partner_id,
                       'origin': 'Test Journal Items',
                       'invoice_state': '2binvoiced',
                       'move_lines': [(0, 0,
                                       {
                                           'product_id': self.product_id.id,
                                           'name': self.product_id.name,
                                           'price_unit': self.product_id.
                                           standard_price,
                                           'product_uom': self.product_id.
                                           uom_id.id,
                                           'product_uom_qty': 2,
                                           'location_id': self.loc_id,
                                           'location_dest_id': self.loc_dest_id
                                       })]
                   })
        # Checking if the picking was created
        self.assertTrue(type(pick_id) in (long, int),
                        'The picking was not created correctly')
        # Validating the picking to create the journal item
        self.picking.action_confirm(cr, uid, [pick_id])
        self.picking.force_assign(cr, uid, [pick_id])
        self.picking.do_transfer(cr, uid, [pick_id])
        pick_brw = self.picking.browse(cr, uid, pick_id)
        # Verifying if the picking was validated
        self.assertTrue(pick_brw.state == 'done',
                        'The picking was not transfered')
        # Creating the invoice from the picking
        value = self.stock_invoice.\
            default_get(cr, uid, [],
                        {'active_model': 'stock.picking',
                         'active_id': pick_id,
                         'active_ids': [pick_id]})
        invo_id = self.stock_invoice.create(cr, uid, value,
                                            {'active_model': 'stock.picking',
                                             'active_id': pick_id,
                                             'active_ids': [pick_id]})
        invoice_ids = self.stock_invoice.\
            create_invoice(cr, uid, [invo_id],
                           {'active_model': 'stock.picking',
                            'active_id': pick_id,
                            'active_ids': [pick_id]})
        # Checking if the invoice was created
        self.assertTrue(len(invoice_ids) > 0,
                        'The invoice was not created')
        # Validating the invoice
        self.invoice.signal_workflow(cr, uid, invoice_ids, 'invoice_open')
        for invo in invoice_ids:
            invo_brw = self.invoice.browse(cr, uid, invo)
            # Checking if the invoices were validated
            self.assertTrue(invo_brw.state == 'open',
                            'The invoice {invo} was not '
                            'validated'.format(invo=invo_brw.name))
        # Get the account move line created from the picking
        p_move_ids = self.move_line.search(cr, uid,
                                           [('ref', '=', pick_brw.name),
                                            ('product_id', '=',
                                             self.product_id.id)])
        # Get the account rounding to compare results
        prec = self.decimal.precision_get(cr, uid, 'Account')
        for line in self.move_line.browse(cr, uid, p_move_ids):
            # Verifying if the total is according to the account rounding
            self.assertTrue(line.credit or line.debit ==
                            float_round(self.product_id.standard_price * 2,
                                        precision_digits=prec),
                            'The amount in the journal item created from the '
                            'picking is wrong computed')
