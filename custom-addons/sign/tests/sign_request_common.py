# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import Command
from odoo.tools import file_open
from odoo.tests.common import TransactionCase, new_test_user

class SignRequestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with file_open('sign/static/demo/sample_contract.pdf', "rb") as f:
            pdf_content = f.read()

        cls.attachment = cls.env['ir.attachment'].create({
            'type': 'binary',
            'raw': pdf_content,
            'name': 'test_employee_contract.pdf',
        })

        cls.role_customer = cls.env.ref('sign.sign_item_role_customer')
        cls.role_customer.change_authorized = False
        cls.role_employee = cls.env.ref('sign.sign_item_role_employee')
        cls.role_employee.change_authorized = False
        cls.role_company = cls.env.ref('sign.sign_item_role_company')
        cls.role_company.change_authorized = True

        cls.template_no_item = cls.env['sign.template'].create({
            'name': 'template_no_item',
            'attachment_id': cls.attachment.id,
        })

        cls.template_1_role = cls.env['sign.template'].create({
            'name': 'template_1_role',
            'attachment_id': cls.attachment.id,
        })
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_customer').id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': cls.template_1_role.id,
                'width': 0.150,
                'height': 0.015,
            }
        ])
        cls.single_role_customer_sign_values = cls.create_sign_values(cls, cls.template_1_role.sign_item_ids, cls.role_customer.id)

        cls.template_3_roles = cls.env['sign.template'].create({
            'name': 'template_3_roles',
            'attachment_id': cls.attachment.id,
        })
        cls.env['sign.item'].create([
            {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_customer').id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': cls.template_3_roles.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.373,
                'posY': 0.258,
                'template_id': cls.template_3_roles.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': cls.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'responsible_id': cls.env.ref('sign.sign_item_role_company').id,
                'page': 1,
                'posX': 0.373,
                'posY': 0.358,
                'template_id': cls.template_3_roles.id,
                'width': 0.150,
                'height': 0.015,
            },
        ])

        cls.signature_fake = base64.b64encode(b"fake_signature")
        cls.customer_sign_values = cls.create_sign_values(cls, cls.template_3_roles.sign_item_ids, cls.role_customer.id)
        cls.employee_sign_values = cls.create_sign_values(cls, cls.template_3_roles.sign_item_ids, cls.role_employee.id)
        cls.company_sign_values = cls.create_sign_values(cls, cls.template_3_roles.sign_item_ids, cls.role_company.id)

        cls.user_1 = new_test_user(cls.env, login="user_1", groups='sign.group_sign_user')
        cls.partner_1 = cls.user_1.partner_id
        cls.partner_1.write({
            'name': 'Laurie Poiret',
            'street': '57 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poiret.a@example.com',
        })

        cls.user_2 = new_test_user(cls.env, login="user_2", groups='sign.group_sign_user')
        cls.partner_2 = cls.user_2.partner_id
        cls.partner_2.write({
            'name': 'Bernardo Ganador',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543209',
            'email': 'bernardo.ganador.a@example.com',
        })

        cls.user_3 = new_test_user(cls.env, login="user_3", groups='sign.group_sign_user')
        cls.partner_3 = cls.user_3.partner_id
        cls.partner_3.write({
            'name': 'Martine Poulichette',
            'street': '59 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543211',
            'email': 'martine.poulichette.a@example.com',
        })

        cls.user_4 = new_test_user(cls.env, login="user_4", groups='sign.group_sign_user')
        cls.partner_4 = cls.user_4.partner_id
        cls.partner_4.write({
            'name': 'Ignasse Reblochon',
            'street': '60 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543212',
            'email': 'ignasse.reblochon.a@example.com',
        })

        cls.user_5 = new_test_user(cls.env, login="user_5", groups='base.group_user')
        cls.partner_5 = cls.user_5.partner_id
        cls.partner_5.write({
            'name': 'Char Aznable',
            'street': '61 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': cls.env.ref("base.be").id,
            'phone': '+0032476543213',
            'email': 'char.aznable.a@example.com',
        })

    def create_sign_request_no_item(self, signer, cc_partners, no_sign_mail=False):
        sign_request = self.env['sign.request'].with_context(no_sign_mail=no_sign_mail).create({
            'template_id': self.template_no_item.id,
            'reference': self.template_no_item.display_name,
            'request_item_ids': [Command.create({
                'partner_id': signer.id,
                'role_id': self.env.ref('sign.sign_item_role_default').id,
            })],
        })
        sign_request.message_subscribe(partner_ids=cc_partners.ids)
        return sign_request

    def create_sign_request_1_role(self, customer, cc_partners):
        sign_request = self.env['sign.request'].create({
            'template_id': self.template_1_role.id,
            'reference': self.template_1_role.display_name,
            'request_item_ids': [Command.create({
                'partner_id': customer.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
            })],
        })
        sign_request.message_subscribe(partner_ids=cc_partners.ids)
        return sign_request

    def create_sign_request_1_role_sms_auth(self, customer, cc_partners):
        role = self.env.ref('sign.sign_item_role_customer')
        role.auth_method = 'sms'
        return self.create_sign_request_1_role(customer, cc_partners)

    def create_sign_request_3_roles(self, customer, employee, company, cc_partners):
        sign_request = self.env['sign.request'].create({
            'template_id': self.template_3_roles.id,
            'reference': self.template_3_roles.display_name,
            'request_item_ids': [Command.create({
                'partner_id': customer.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
            }), Command.create({
                'partner_id': employee.id,
                'role_id': self.env.ref('sign.sign_item_role_employee').id,
            }), Command.create({
                'partner_id': company.id,
                'role_id': self.env.ref('sign.sign_item_role_company').id,
            })],
        })
        sign_request.message_subscribe(partner_ids=cc_partners.ids)
        return sign_request

    def get_sign_item_config(self, role_id):
        return {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'required': True,
                'option_ids': [],
                'responsible_id': role_id,
                'page': 1,
                'posX': 0.1,
                'posY': 0.2,
                'width': 0.15,
                'height': 0.15
        }

    def create_sign_values(self, sign_item_ids, role_id):
        return {
            str(sign_id): 'a'
            for sign_id in sign_item_ids
            .filtered(lambda r: not r.responsible_id or r.responsible_id.id == role_id)
            .mapped('id')
        }
