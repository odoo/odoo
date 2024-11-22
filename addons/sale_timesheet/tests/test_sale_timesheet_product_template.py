# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestProductTemplate(TestCommonSaleTimesheet):
    def test_delete_master_timesheet_product(self):
        """
            Test that the master timesheet product cannot be deleted, archived nor linked
            to a company but regular products still can.
        """
        time_product = self.env.ref('sale_timesheet.time_product').product_tmpl_id
        with self.assertRaises(ValidationError):
            time_product.unlink()
        with self.assertRaises(ValidationError):
            time_product.write({'active': False})
        with self.assertRaises(ValidationError):
            time_product.write({'company_id': self.env.company.id})

        non_timesheet_product = self.product_delivery_timesheet5.product_tmpl_id
        non_timesheet_product.write({'company_id': self.env.company.id})
        self.assertEqual(non_timesheet_product.company_id, self.env.company)
        non_timesheet_product.write({'active': False})
        self.assertFalse(non_timesheet_product.active)
        non_timesheet_product.unlink()
        self.assertFalse(self.env['product.template'].browse(non_timesheet_product.id).exists())
