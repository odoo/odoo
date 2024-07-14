# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from .sign_request_common import SignRequestCommon
import odoo.tests

from odoo.tools.misc import mute_logger, file_open
from odoo.tools.translate import WEB_TRANSLATION_COMMENT


@odoo.tests.tagged('-at_install', 'post_install')
class TestUi(odoo.tests.HttpCase, SignRequestCommon):
    def test_ui(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.start_tour("/web", 'sign_widgets_tour', login='admin')

        self.start_tour("/web", 'shared_sign_request_tour', login='admin')
        shared_sign_request = self.env['sign.request'].search([('reference', '=', 'template_1_role-Shared'), ('state', '=', 'shared')])
        self.assertTrue(shared_sign_request.exists(), 'A shared sign request should be created')
        signed_sign_request = self.env['sign.request'].search([('reference', '=', 'template_1_role'), ('state', '=', 'signed')])
        self.assertTrue(signed_sign_request.exists(), 'A signed sign request should be created')
        self.assertEqual(signed_sign_request.create_uid, self.env.ref('base.user_admin'), 'The signed sign request should be created by the admin')
        signer = self.env['res.partner'].search([('email', '=', 'mitchell.admin@public.com')])
        self.assertTrue(signer.exists(), 'A partner should exists with the email provided while signing')

    def test_translate_sign_instructions(self):
        fr_lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'fr_FR')])
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [fr_lang.id])]
        }).lang_install()

        # Once `website` is installed, the available langs are only the ones
        # from the website, which by default is just the `en_US` lang.
        langs = self.env['res.lang'].with_context(active_test=False).search([]).get_sorted()
        self.patch(self.registry['res.lang'], 'get_available', lambda self: langs)
        self.partner_1.lang = 'fr_FR'
        sign_request = self.create_sign_request_1_role(customer=self.partner_1, cc_partners=self.env['res.partner'])
        url = f"/sign/document/{sign_request.id}/{sign_request.request_item_ids.access_token}"
        self.start_tour(url, 'translate_sign_instructions', login=None)

    def test_sign_flow(self):
        flow_template = self.template_1_role.copy()
        self.env['sign.item'].create({
            'type_id': self.env.ref('sign.sign_item_type_signature').id,
            'required': True,
            'responsible_id': self.env.ref('sign.sign_item_role_customer').id,
            'page': 1,
            'posX': 0.144,
            'posY': 0.716,
            'template_id': flow_template.id,
            'width': 0.200,
            'height': 0.050,
        })
        with file_open('sign/static/demo/signature.png', "rb") as f:
            img_content = base64.b64encode(f.read())

        self.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'sign_signature': img_content,
        })
        self.start_tour("/web", 'test_sign_flow_tour', login='admin')

    def test_template_edition(self):
        blank_template = self.env['sign.template'].create({
            'name': 'blank_template',
            'attachment_id': self.attachment.id,
        })

        self.start_tour("/web", "sign_template_creation_tour", login="admin")

        self.assertEqual(blank_template.name, 'filled_template', 'The tour should have changed the template name')
        self.assertEqual(len(blank_template.sign_item_ids), 4)
        self.assertEqual(blank_template.responsible_count, 2)
        self.assertEqual(set(blank_template.sign_item_ids.mapped("type_id.item_type")), {"text", "signature", "selection"})
        selection_sign_item = blank_template.sign_item_ids.filtered(lambda item: item.type_id.item_type == 'selection')
        self.assertEqual(len(selection_sign_item.option_ids), 1)
        self.assertEqual(selection_sign_item.option_ids[0].value, "option")
        self.assertEqual(set(blank_template.sign_item_ids.mapped("name")), set(["Name", "Signature", "placeholder", "Selection"]))

    def test_report_modal(self):
        self.start_tour("/web", "sign_report_modal_tour", login="admin")
