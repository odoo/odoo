# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestProjectMrpProduction(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Product = cls.env['product.product']
        cls.finished = Product.create({'name': 'Finished', 'type': 'consu'})
        cls.comp1 = Product.create({'name': 'Component 1', 'type': 'consu'})
        cls.comp2 = Product.create({'name': 'Component 2', 'type': 'consu'})
        cls.project = cls.env['project.project'].create({'name': 'Hand-set project'})
        cls.project_bom = cls.env['project.project'].create({'name': 'BoM project'})
        BoM = cls.env['mrp.bom']
        bom_vals = {
            'product_tmpl_id': cls.finished.product_tmpl_id.id,
            'bom_line_ids': [(0, 0, {'product_id': cls.comp1.id, 'product_qty': 1})],
        }
        cls.bom = BoM.create(bom_vals)
        cls.bom_2 = BoM.create(bom_vals)
        cls.bom_with_project = BoM.create({**bom_vals, 'project_id': cls.project_bom.id})

    def _create_mo(self, bom, **kwargs):
        return self.env['mrp.production'].create({
            'product_id': self.finished.id,
            'bom_id': bom.id,
            **kwargs,
        })

    def _check_update_bom_keeps_project(self, confirm):
        mo = self._create_mo(self.bom)
        mo.project_id = self.project
        if confirm:
            mo.action_confirm()
        self.bom.bom_line_ids = [(0, 0, {'product_id': self.comp2.id, 'product_qty': 2})]
        self.assertTrue(mo.is_outdated_bom)
        mo.action_update_bom()
        self.assertEqual(mo.project_id, self.project)

    def test_update_bom_keeps_project(self):
        self._check_update_bom_keeps_project(confirm=False)

    def test_update_bom_keeps_project_confirmed(self):
        self._check_update_bom_keeps_project(confirm=True)

    def test_change_bom_keeps_project(self):
        mo = self._create_mo(self.bom)
        mo.project_id = self.project
        mo.bom_id = self.bom_2
        self.assertEqual(mo.project_id, self.project)

    def test_bom_project_applied(self):
        mo = self._create_mo(self.bom_with_project)
        self.assertEqual(mo.project_id, self.project_bom)

        mo = self._create_mo(self.bom)
        mo.project_id = self.project
        mo.bom_id = self.bom_with_project
        self.assertEqual(mo.project_id, self.project_bom)

    def test_from_project_action_context(self):
        MrpProduction = self.env['mrp.production'].with_context(
            default_project_id=self.project.id,
            from_project_action=True,
        )
        for bom in (self.bom, self.bom_with_project):
            mo = MrpProduction.create({
                'product_id': self.finished.id,
                'bom_id': bom.id,
            })
            self.assertEqual(mo.project_id, self.project)
