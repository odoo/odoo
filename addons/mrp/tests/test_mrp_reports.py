from odoo.tests import HttpCase, tagged
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestReportBom(HttpCase):

    def test_mrp_report_bom_variant_selection(self):
        self.env.ref('base.user_admin').write({'group_ids': [
            Command.link(self.env.ref('product.group_product_variant').id),
        ]})

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
