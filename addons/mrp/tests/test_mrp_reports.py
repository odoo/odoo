from odoo.tests import HttpCase, tagged
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestReportBom(HttpCase):

    def test_mrp_report_bom_variant_selection(self):
        attribute = self.env['product.attribute'].create({'name': 'Size'})
        value_S, value_L = self.env['product.attribute.value'].create([
            {'name': 'S', 'attribute_id': attribute.id},
            {'name': 'L', 'attribute_id': attribute.id}
        ])

        product_tmpl = self.env['product.template'].create({
            'name': 'Product Test Sync',
            'type': 'consu',
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set([value_S.id, value_L.id])]
            })]
        })

        [variant_s, variant_l] = product_tmpl.product_variant_ids

        variant_s.default_code = 'zebra'
        variant_l.default_code = 'alpaca'

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product_tmpl.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        action_id = self.env.ref('mrp.action_report_mrp_bom')
        url = "/web#action=%s&active_id=%s" % (str(action_id.id), str(bom.id))
        self.start_tour(url, "mrp_bom_report_tour", login="admin")

    def test_mrp_report_overview_bom_cost(self):
        """
        Test that the BoM cost in the MO overview is correctly calculated when the BoM's base
        quantity is greater than 1.
        """
        manufactured = self.env['product.product'].create({
            'name': 'Manufactured',
            'is_storable': True,
            'standard_price': 10,
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
            'standard_price': 10,
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': manufactured.product_tmpl_id.id,
            'product_qty': 10,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 1}),
            ],
        })
        mo = self.env['mrp.production'].create({
            'bom_id': bom.id,
        })
        mo.action_confirm()
        report_data = self.env['report.mrp.report_mo_overview']._get_report_data(mo.id)
        self.assertEqual(report_data['components'][0]['replenishments'][0]['summary']['bom_cost'], 10.0)
