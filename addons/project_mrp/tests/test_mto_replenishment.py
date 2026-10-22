# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMtoReplenishment(TransactionCase):

    def test_child_mo_project(self):
        """ The MO replenishing a component in MTO gets the project of the MO
        consuming it, with the component moved directly or through a picking. """
        warehouse = self.env.ref('stock.warehouse0')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        project = self.env['project.project'].create({'name': 'Project'})
        for steps in ('mrp_one_step', 'pbm_sam'):
            with self.subTest(manufacture_steps=steps):
                warehouse.manufacture_steps = steps
                raw, component, finished = self.env['product.product'].create([{
                    'name': 'Raw',
                }, {
                    'name': 'Component',
                    'is_storable': True,
                    'route_ids': [Command.set((mto_route | self.env.ref('mrp.route_warehouse0_manufacture')).ids)],
                }, {
                    'name': 'Finished',
                    'is_storable': True,
                }])
                self.env['mrp.bom'].create([{
                    'product_tmpl_id': component.product_tmpl_id.id,
                    'bom_line_ids': [Command.create({'product_id': raw.id, 'product_qty': 1})],
                }, {
                    'product_tmpl_id': finished.product_tmpl_id.id,
                    'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1})],
                }])
                production = self.env['mrp.production'].create({
                    'product_id': finished.id,
                    'project_id': project.id,
                })
                production.action_confirm()

                child = production._get_children()
                self.assertEqual(child.product_id, component)
                self.assertEqual(child.project_id, project)
