# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.product_matrix.tests.common import TestMatrixCommon


class TestProductMatrix(TestMatrixCommon):

    def test_matrix_too_many_combinations(self):
        """ Check that the grid is refused instead of being built when the product has
        more attribute combinations than the limit (2^4 * 9^4 = 104976).
        """
        dynamic_attrs = self.env['product.attribute'].create([{
            'name': f"Attribute {i}",
            'create_variant': 'dynamic',
            'value_ids': [Command.create({'name': f"Value {j}"}) for j in range(1, 10)],
        } for i in range(1, 5)])
        self.matrix_template.attribute_line_ids = [Command.create({
            'attribute_id': attr.id,
            'value_ids': [Command.set(attr.value_ids.ids)],
        }) for attr in dynamic_attrs]

        with self.assertRaises(UserError):
            self.matrix_template._get_template_matrix()
