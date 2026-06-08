# -*- coding: utf-8 -*-

from odoo import Command
from odoo.tests import Form, HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSubcontractingPortalUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1. Create portal user
        user = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nolog': True}).create({
            'name': 'Georges',
            'login': 'georges1',
            'password': 'georges1',
            'email': 'georges@project.portal',
            'signature': 'SignGeorges',
            'notification_type': 'email',
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
        })

        cls.partner_portal = cls.env['res.partner'].with_context({'mail_create_nolog': True}).create({
            'name': 'Georges',
            'email': 'georges@project.portal',
            'company_id': False,
            'user_ids': [user.id],
        })
        # 2. Create a BOM of subcontracting type
        cls.comp = cls.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
        })

        cls.finished_product = cls.env['product.product'].create({
            'name': 'Finished',
            'is_storable': True,
        })
        bom_form = Form(cls.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.subcontractor_ids.add(cls.partner_portal)
        bom_form.product_tmpl_id = cls.finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp
            bom_line.product_qty = 1
        cls.bom_tracked = bom_form.save()

    def test_subcontrating_portal(self):
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.partner_portal
        with picking_form.move_ids.new() as move:
            move.product_id = self.finished_product
            move.product_uom_qty = 2
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        self.start_tour("/my/productions", 'subcontracting_portal_tour', login="georges1")
