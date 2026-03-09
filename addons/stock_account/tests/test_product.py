# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.fields import Command
from odoo.tests import tagged


class TestStockAccountProduct(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fifo_category = cls.env['product.category'].create({
            'name': 'All/Saleable FIFO',
            'parent_id': cls.env.ref('product.product_category_all').id,
            'property_cost_method': 'fifo',
        })
        cls.attribute_legs = cls.env['product.attribute'].create({
            'name': 'Legs',
            'value_ids': [
                Command.create({'name': 'Steel'}),
                Command.create({'name': 'Aluminium'}),
                Command.create({'name': 'Custom'}),
            ],
        })

    def test_update_categ_and_add_attributes(self):
        """ Check that one can adapt the `property_cost_method` of a product with variants."""
        template = self.env['product.template'].create({
            'name': 'Table',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.attribute_legs.id,
                    'value_ids': [
                        Command.link(self.attribute_legs.value_ids[0].id),  # Add Steel
                        Command.link(self.attribute_legs.value_ids[1].id),  # Add Aluminium
                ]}),
            ],
        })
        initial_variants = template.product_variant_ids
        self.assertEqual(len(initial_variants), 2, "Expected 2 initial variants.")
        template.write({
            'categ_id': self.fifo_category.id,
            'attribute_line_ids': [Command.update(template.attribute_line_ids[0].id, {
                'value_ids': [
                    Command.unlink(self.attribute_legs.value_ids[0].id),  # Remove Steel
                    Command.link(self.attribute_legs.value_ids[2].id),  # Add Custom
                ]
            })]
        })
        final_variants = template.product_variant_ids
        self.assertEqual(len(final_variants), 2, "Expected 2 product variants after attribute change.")

    def test_total_value_as_restricted_user(self):
        """
        total_value (compute_sudo=True) calls qty_available, which internally
        calls _compute_quantities_dict → _bom_find (when MRP is installed).
        The original code used sudo(False) which caused an AccessError for users
        without mrp.bom read access (e.g. POS operators). Verify that computing
        total_value as a user without stock manager access does not raise.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self._make_in_move(self.product1, 10, unit_cost=5.0)

        # Simulate a restricted user (e.g. POS operator): no stock manager group
        restricted_user = self.env['res.users'].create({
            'name': 'POS Operator',
            'login': 'pos_operator_test',
            'groups_id': [Command.set([self.env.ref('base.group_user').id])],
        })
        # total_value is declared with compute_sudo=True, so reading it runs _compute_value_svl as superuser
        total_value = self.product1.with_user(restricted_user).total_value
        self.assertAlmostEqual(total_value, 50.0)


@tagged('post_install', '-at_install')
class TestStockAccountProductMultiCompany(TestStockValuationCommon):
    def test_total_value_scoped_to_current_company(self):
        """
        total_value uses compute_sudo=True, meaning it runs as superuser.
        Ensure qty_available inside the compute is restricted to the current
        company and does not aggregate stock from all active companies.
        """
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Company B'})
        self.env.user.write({
            'company_ids': [Command.set([company_a.id, company_b.id])],
            'company_id': company_a.id,
        })

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.with_company(company_b).product_tmpl_id.categ_id.property_cost_method = 'average'

        warehouse_b = self.env['stock.warehouse'].sudo().search([('company_id', '=', company_b.id)], limit=1)
        if not warehouse_b:
            warehouse_b = self.env['stock.warehouse'].sudo().create({
                'name': 'WH-B', 'code': 'WH-B', 'company_id': company_b.id,
            })

        self.env.user.company_id = company_a
        self._make_in_move(self.product1, 10, unit_cost=5.0)

        self.env.user.company_id = company_b
        self._make_in_move(
            self.product1, 20, unit_cost=3.0,
            create_picking=True,
            loc_dest=warehouse_b.lot_stock_id,
            pick_type=warehouse_b.in_type_id,
        )

        product_sudo = self.product1.sudo().with_context(
            allowed_company_ids=[company_a.id, company_b.id],
            company_id=company_a.id,
        )
        aggregates = (50.0, 10.0)  # value_sum=50, quantity_sum=10 → avg_cost=5
        vals = product_sudo._prepare_valuation_layer_field_values(aggregates)
        self.assertAlmostEqual(vals['total_value'], 50.0,
            msg="total_value in sudo must not aggregate qty_available from all companies")

        product_sudo_b = self.product1.sudo().with_context(
            allowed_company_ids=[company_b.id, company_a.id],
            company_id=company_b.id,
        )
        aggregates_b = (60.0, 20.0)  # value_sum=60, quantity_sum=20 → avg_cost=3
        vals_b = product_sudo_b._prepare_valuation_layer_field_values(aggregates_b)
        self.assertAlmostEqual(vals_b['total_value'], 60.0,
            msg="total_value in sudo must not aggregate qty_available from all companies")
