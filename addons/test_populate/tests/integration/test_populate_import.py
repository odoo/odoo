from odoo.addons.populate import start_populate
from odoo.addons.test_populate.tests.common import PopulateTestCase


class TestImportedBlueprintExecution(PopulateTestCase):

    def test_namespaced_import_executes_with_internal_and_target_refs(self):
        caller = self.env.ref('test_populate.sample_import_caller_blueprint')
        session = self.env['populate.session'].create({
            'blueprint_id': caller.id,
            'worker_count': 1,
        })

        start_populate(session)

        model_data = self.env['populate.model.data'].search([('session_id', '=', session.id)])
        self.assertEqual(set(model_data.mapped('ref')), {'catalog/suppliers', 'catalog/products'})
        products = self.env['test_populate.product'].browse(
            model_data.filtered(lambda data: data.ref == 'catalog/products').mapped('res_id'),
        )
        suppliers = self.env['test_populate.supplier'].browse(
            model_data.filtered(lambda data: data.ref == 'catalog/suppliers').mapped('res_id'),
        )
        self.assertEqual(len(products), 4)
        self.assertFalse(products.filtered(lambda product: not product.supplier_id))
        self.assertLessEqual(set(products.supplier_id.ids), set(suppliers.ids))
        self.assertEqual(set(products.mapped('description')), {'Imported product'})
