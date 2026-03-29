from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestPurchaseUserAccessFlow(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_user = cls.env['res.users'].create({
            'company_id': cls.env.ref('base.main_company').id,
            'name': "Purchase J. User",
            'login': "puser",
            'email': "pj@us.er",
            'group_ids': [Command.set([cls.env.ref('purchase.group_purchase_user').id])],
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'P. Artner',
            'email': 'p@rtn.er',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Acme Hotdog',
            'type': 'consu',
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product.id,
                    'product_qty': 5.0,
                }),
            ],
        })

    def test_purchase_user_access_flow(self):
        """Test whether the purchase user can access the bills
           and pickings related to a purchase order."""
        self.purchase_order.button_confirm()
        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'purchase_line_id': self.purchase_order.order_line.id,
                    'quantity': 5.0,
                }),
            ],
        }).action_post()

        self.start_tour('/odoo/purchase/%d' % self.purchase_order.id,
                        'test_purchase_user_access_flow',
                        login=self.purchase_user.login)
