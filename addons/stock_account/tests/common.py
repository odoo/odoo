from odoo import Command
from odoo.tools.misc import clean_context
from odoo.tests import Form
from odoo.addons.base.tests.common import BaseCommon


class TestStockValuationCommon(BaseCommon):
    # Override
    @classmethod
    def _create_company(cls, **create_values):
        company = super()._create_company(**create_values)
        cls.env["account.chart.template"]._load(
            "generic_coa", company, install_demo=False
        )
        return company

    # HELPER
    def _create_account_move(self, move_type, product, quantity=1.0, price_unit=1.0, post=True, **kwargs):
        invoice_vals = {
            "partner_id": self.vendor.id,
            "move_type": move_type,
            "invoice_line_ids": [],
        }
        if kwargs.get('reversed_entry_id'):
            invoice_vals["reversed_entry_id"] = kwargs['reversed_entry_id']
        invoice = self.env["account.move"].create(invoice_vals)
        product_uom = kwargs.get('product_uom') or product.uom_id
        self.env["account.move.line"].create({
            "move_id": invoice.id,
             "display_type": "product",
             "name": "test line",
             "price_unit": price_unit,
             "quantity": quantity,
             "product_id": product.id,
             "product_uom_id": product_uom.id,
             "tax_ids": [(5, 0, 0)],
        })
        if post:
            invoice.action_post()
        return invoice

    def _create_invoice(self, product, quantity=1.0, price_unit=None, post=True, **kwargs):
        return self._create_account_move("out_invoice", product, quantity, price_unit, post, **kwargs)

    def _create_bill(self, product, quantity=1.0, price_unit=None, post=True, **kwargs):
        return self._create_account_move("in_invoice", product, quantity, price_unit, post, **kwargs)

    def _create_credit_note(self, product, quantity=1.0, price_unit=1.0, post=True, **kwargs):
        move_type = kwargs.pop("move_type", "out_refund")
        return self._create_account_move(move_type, product, quantity, price_unit, post, **kwargs)

    def _close(self, auto_post=True, at_date=None):
        action = self.company.action_close_stock_valuation(at_date=at_date, auto_post=auto_post)
        return action['res_id'] and self.env['account.move'].browse(action['res_id'])

    def _use_inventory_location_accounting(self):
        self.account_inventory = self.env['account.account'].create({
            'name': 'Inventory Account',
            'code': '100101',
            'account_type': 'asset_current',
        })
        inventory_locations = self.env['stock.location'].search([('usage', '=', 'inventory'), ('company_id', '=', self.company.id)])
        inventory_locations.valuation_account_id = self.account_inventory.id
        return self.account_inventory

    # Moves
    def _make_in_move(self,
            product,
            quantity,
            unit_cost=None,
            create_picking=False,
            **kwargs,
        ):
        """ Helper to create and validate a receipt move.

        :param product: Product to move
        :param quantity: Quantity to move
        :param unit_cost: Price unit
        :param create_picking: Create the picking containing the created move
        :param **kwargs: stock.move fields that you can override
            ''location_id: origin location for the move
            ''location_dest_id: destination location for the move
            ''lot_ids: list of lot (split among the quantity)
            ''picking_type_id: picking type
            ''uom_id: Unit of measure
            ''owner_id: Consignment owner
        """
        unit_cost = unit_cost or product.standard_price
        product_qty = quantity
        if kwargs.get('uom_id'):
            uom = self.env['uom.uom'].browse(kwargs.get('uom_id'))
            product_qty = uom._compute_quantity(quantity, product.uom_id)
        move_vals = {
            'product_id': product.id,
            'location_id': kwargs.get('location_id', self.supplier_location.id),
            'location_dest_id': kwargs.get('location_dest_id', self.stock_location.id),
            'product_uom': kwargs.get('uom_id', self.uom.id),
            'product_uom_qty': quantity,
            'picking_type_id': kwargs.get('picking_type_id', self.picking_type_in.id),
        }
        if unit_cost:
            move_vals['value_manual'] = unit_cost * product_qty
        in_move = self.env['stock.move'].create(move_vals)

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': in_move.picking_type_id.id,
                'location_id': in_move.location_id.id,
                'location_dest_id': in_move.location_dest_id.id,
                'owner_id': kwargs.get('owner_id', False),
                })
            in_move.picking_id = picking.id

        in_move._action_confirm()
        lot_ids = kwargs.get('lot_ids')
        if lot_ids:
            in_move.move_line_ids.unlink()
            in_move.move_line_ids = [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': in_move.location_dest_id,
                'quantity': quantity / len(lot_ids),
                'product_id': product.id,
                'lot_id': lot.id,
            }) for lot in lot_ids]
        else:
            in_move._action_assign()

        if not create_picking and kwargs.get('owner_id'):
            in_move.move_line_ids.owner_id = kwargs.get('owner_id')

        in_move.picked = True
        in_move._action_done()

        return in_move

    def _make_out_move(self,
        product,
        quantity,
        force_assign=True,
        create_picking=False,
        **kwargs,
    ):
        """ Helper to create and validate a delivery move.

        :param product: Product to move
        :param quantity: Quantity to move
        :param force_assign: Bypass reservation to force the required quantity
        :param create_picking: Create the picking containing the created move
        :param **kwargs: stock.move fields that you can override
            ''location_id: origin location for the move
            ''location_dest_id: destination location for the move
            ''lot_ids: list of lot (split among the quantity)
            ''picking_type_id: picking type
            ''uom_id: Unit of measure
            ''owner_id: Consignment owner
        """
        out_move = self.env['stock.move'].create({
            'product_id': product.id,
            'location_id': kwargs.get('location_id', self.stock_location.id),
            'location_dest_id': kwargs.get('location_dest_id', self.customer_location.id),
            'product_uom': kwargs.get('uom_id', self.uom.id),
            'product_uom_qty': quantity,
            'picking_type_id': kwargs.get('picking_type_id', self.picking_type_out.id),
        })

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': out_move.picking_type_id.id,
                'location_id': out_move.location_id.id,
                'location_dest_id': out_move.location_dest_id.id,
                })
            out_move.picking_id = picking.id

        out_move._action_confirm()
        out_move._action_assign()
        lot_ids = kwargs.get('lot_ids')
        if lot_ids:
            out_move.move_line_ids.unlink()
            out_move.move_line_ids = [Command.create({
                'location_id': out_move.location_id.id,
                'location_dest_id': self.customer_location.id,
                'quantity': quantity / len(lot_ids),
                'product_id': product.id,
                'lot_id': lot.id,
            }) for lot in lot_ids]
        elif force_assign:
            out_move.quantity = quantity
        out_move.picked = True
        out_move._action_done()

        return out_move

    def _make_dropship_move(self, product, quantity, unit_cost=None, lot_ids=None):
        dropshipped = self.env['stock.move'].create({
            'product_id': product.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.customer_location.id,
            'product_uom': self.uom.id,
            'product_uom_qty': quantity,
            'picking_type_id': self.picking_type_out.id,
        })
        if unit_cost:
            dropshipped.price_unit = unit_cost
        dropshipped._action_confirm()
        dropshipped._action_assign()
        if lot_ids:
            dropshipped.move_line_ids = [Command.clear()]
            dropshipped.move_line_ids = [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': self.customer_location.id,
                'quantity': quantity / len(lot_ids),
                'product_id': product.id,
                'lot_id': lot.id,
            }) for lot in lot_ids]
        else:
            dropshipped.move_line_ids.quantity = quantity
        dropshipped.picked = True
        dropshipped._action_done()
        return dropshipped

    def _make_return(self, move, quantity_to_return):
        stock_return_picking = Form(self.env['stock.return.picking']
            .with_context(active_ids=[move.picking_id.id], active_id=move.picking_id.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking.save()
        stock_return_picking.product_return_moves.quantity = quantity_to_return
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].quantity = quantity_to_return
        return_pick.move_ids[0].picked = True
        return_pick._action_done()
        return return_pick.move_ids

    # Post move processing
    def _add_move_line(self, move, **kwargs):
        old_price_unit = move._get_price_unit()
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        } | kwargs)
        move.value_manual = old_price_unit * move.quantity

    def _set_quantity(self, move, quantity):
        """Helper function to retroactively change the quantity of a move.
           The total value of the product will be recomputed as a result,
           regardless of the valuation method."""
        price_unit = move._get_price_unit()
        move.quantity = quantity
        move.value_manual = price_unit * quantity

    # GETTER
    def _get_stock_valuation_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.account_stock_valuation.id),
        ], order='date, id')

    def _get_expense_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.account_expense.id),
        ], order='date, id')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Inventory Test Company'})
        cls.env["account.chart.template"]._load(
            "generic_coa", cls.company, install_demo=False
        )
        cls.env.user.company_id = cls.company
        cls.inventory_user = cls._create_new_internal_user(name='Pauline Poivraisselle', login='pauline', groups='stock.group_stock_user')
        cls.owner = cls._create_partner(name='Consignment Owner')
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TW',
            'company_id': cls.company.id,
        })
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')

        cls.account_expense = cls.company.expense_account_id
        cls.account_stock_valuation = cls.company.account_stock_valuation_id
        cls.account_stock_variation = cls.account_stock_valuation.account_stock_variation_id
        cls.account_payable = cls.company.partner_id.property_account_payable_id
        cls.account_receivable = cls.company.partner_id.property_account_receivable_id

        cls.picking_type_in = cls.warehouse.in_type_id
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.uom = cls.env.ref('uom.product_uom_unit')

        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'company_id': cls.company.id,
        })
        cls.other_company = cls._create_company(name="Other Company")
        cls.branch = cls._create_company(name="Branch Company", parent_id=cls.company.id)
        cls.other_currency = cls.setup_other_currency(code="EUR", rates=[
            ('1900-01-01', 1.0),
            ('2016-01-01', 3.0),
            ('2017-01-01', 2.0),
        ])

        cls.category_standard = cls.env['product.category'].create({
            'name': 'Standard',
            'property_valuation': 'periodic',
            'property_cost_method': 'standard',
        })
        cls.category_standard_auto = cls.category_standard.copy({
            'name': 'Standard Auto',
            'property_valuation': 'real_time',
        })
        cls.category_fifo = cls.env['product.category'].create({
            'name': 'Fifo',
            'property_valuation': 'periodic',
            'property_cost_method': 'fifo',
        })
        cls.category_fifo_auto = cls.category_fifo.copy({
            'name': 'Fifo Auto',
            'property_valuation': 'real_time',
        })
        cls.category_avco = cls.env['product.category'].create({
            'name': 'Avco',
            'property_valuation': 'periodic',
            'property_cost_method': 'average',
        })
        cls.category_avco_auto = cls.category_avco.copy({
            'name': 'Avco Auto',
            'property_valuation': 'real_time',
        })

        # Clean context to avoid magic behavior later (e.g. copy with create_product_product to false)
        product_common_vals = {
            "standard_price": 10.0,
            "list_price": 20.0,
            "uom_id": cls.uom.id,
            "is_storable": True,
        }
        cls.product_standard = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Standard Product',
            'categ_id': cls.category_standard.id,
        }).with_context(clean_context(cls.env.context))
        cls.product_standard_auto = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Standard Product Auto',
            'categ_id': cls.category_standard_auto.id,
        }).with_context(clean_context(cls.env.context))
        cls.product_fifo = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Fifo Product',
            'categ_id': cls.category_fifo.id,
        }).with_context(clean_context(cls.env.context))
        cls.product_fifo_auto = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Fifo Product Auto',
            'categ_id': cls.category_fifo_auto.id,
        }).with_context(clean_context(cls.env.context))
        cls.product_avco = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Avco Product',
            'categ_id': cls.category_avco.id,
        }).with_context(clean_context(cls.env.context))
        cls.product_avco_auto = cls.env['product.product'].create({
            **product_common_vals,
            'name': 'Avco Product Auto',
            'categ_id': cls.category_avco_auto.id,
        }).with_context(clean_context(cls.env.context))
