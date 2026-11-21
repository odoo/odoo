# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, TransactionCase


class TestProductionOwner(TransactionCase):
    """ Contract processing: herbs of a customer, stocked as their consignment, are cut and sieved
    into tea cut and dust (by-product), which still belong to the customer. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('stock.group_tracking_owner') | cls.env.ref('stock.group_production_lot')
        cls.stock_location = cls.env.ref('stock.warehouse0').lot_stock_id
        cls.customer, cls.other_customer = cls.env['res.partner'].create([{'name': 'Herb Trader'}, {'name': 'Tea Shop'}])
        cls.herb, cls.tea_cut, cls.dust = cls.env['product.product'].create([
            {'name': name, 'is_storable': True}
            for name in ('Nettle leaves', 'Nettle tea cut', 'Nettle dust')
        ])
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.tea_cut.product_tmpl_id.id,
            'product_qty': 9,
            'bom_line_ids': [Command.create({'product_id': cls.herb.id, 'product_qty': 10})],
            'byproduct_ids': [Command.create({'product_id': cls.dust.id, 'product_qty': 1})],
        })

    def _add_herbs(self, quantity, owner=None):
        self.env['stock.quant']._update_available_quantity(self.herb, self.stock_location, quantity, owner_id=owner)

    def _create_mo(self, quantity=9):
        production = self.env['mrp.production'].create({
            'product_id': self.tea_cut.id,
            'bom_id': self.bom.id,
            'product_qty': quantity,
        })
        production.action_confirm()
        production.action_assign()
        return production

    def _produce(self, production, quantity=None):
        with Form(production) as production_form:
            production_form.qty_producing = quantity or production.product_qty
        return production.button_mark_done()

    def _owned_quantity(self, product, owner):
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id), ('location_id', '=', self.stock_location.id), ('owner_id', '=', owner.id),
        ])
        return sum(quants.mapped('quantity'))

    def test_owner_from_components(self):
        """ The owner of the components is proposed, and the finished product and the by-product are theirs. """
        self._add_herbs(10, owner=self.customer)
        production = self._create_mo()
        self.assertEqual(production.owner_id, self.customer)

        self._produce(production)
        self.assertEqual(production.state, 'done')
        self.assertEqual(self._owned_quantity(self.tea_cut, self.customer), 9)
        self.assertEqual(self._owned_quantity(self.dust, self.customer), 1)
        self.assertFalse(self._owned_quantity(self.tea_cut, self.env['res.partner']))
        self.assertEqual(self.tea_cut.qty_available, 9)

    def test_mixed_owners(self):
        """ Components of several owners: no owner is proposed, the one set by hand is used. """
        self._add_herbs(5, owner=self.customer)
        self._add_herbs(5, owner=self.other_customer)
        production = self._create_mo()
        self.assertFalse(production.owner_id)

        production.owner_id = self.other_customer
        self._produce(production)
        self.assertEqual(self._owned_quantity(self.tea_cut, self.other_customer), 9)
        self.assertEqual(self._owned_quantity(self.dust, self.other_customer), 1)

    def test_partly_owned_components(self):
        """ Components partly of the company: no owner is proposed, and the products are the company's. """
        self._add_herbs(5, owner=self.customer)
        self._add_herbs(5)
        production = self._create_mo()
        self.assertFalse(production.owner_id)

        self._produce(production)
        self.assertEqual(self._owned_quantity(self.tea_cut, self.env['res.partner']), 9)

    def test_no_owner(self):
        """ Without consignment, nothing changes. """
        self._add_herbs(10)
        production = self._create_mo()
        self.assertFalse(production.owner_id)

        self._produce(production)
        self.assertFalse(production.move_finished_ids.move_line_ids.owner_id)
        self.assertEqual(self._owned_quantity(self.tea_cut, self.env['res.partner']), 9)

    def test_owner_with_lot(self):
        """ The produced lot is stocked with the owner. """
        self.tea_cut.tracking = 'lot'
        self._add_herbs(10, owner=self.customer)
        production = self._create_mo()
        production.action_generate_serial()
        lot = production.lot_producing_ids
        self.assertTrue(lot)

        self._produce(production)
        quant = self.env['stock.quant'].search([('product_id', '=', self.tea_cut.id), ('location_id', '=', self.stock_location.id)])
        self.assertRecordValues(quant, [{'lot_id': lot.id, 'owner_id': self.customer.id, 'quantity': 9}])

    def test_backorder_keeps_owner(self):
        self._add_herbs(20, owner=self.customer)
        production = self._create_mo(quantity=18)
        action = self._produce(production, quantity=9)
        Form.from_action(self.env, action).save().action_backorder()

        backorder = production.production_group_id.production_ids - production
        self.assertEqual(backorder.owner_id, self.customer)
        self._produce(backorder)
        self.assertEqual(self._owned_quantity(self.tea_cut, self.customer), 18)

    def test_unbuild_keeps_owner(self):
        """ Unbuilding the products of a customer gives their components back to them. """
        self._add_herbs(10, owner=self.customer)
        production = self._create_mo()
        self._produce(production)

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = production
        unbuild_form.save().action_unbuild()
        self.assertEqual(self._owned_quantity(self.herb, self.customer), 10)
        self.assertFalse(self._owned_quantity(self.tea_cut, self.customer))
        self.assertFalse(self._owned_quantity(self.herb, self.env['res.partner']))
