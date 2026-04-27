# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import Command
from odoo.tests.common import HttpCase, tagged
from odoo.tools import file_open, mute_logger


@tagged('-at_install', 'post_install')
class TestSalaryPackageItems(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.structure_type = cls.env['hr.payroll.structure.type'].create({'name': 'struct'})
        cls.default_contract = cls.env['hr.contract'].create({
            'name': "Test Default Contract",
            'employee_id': False,
            'wage': 1000,
            'structure_type_id': cls.structure_type.id,
        })
        cls.job = cls.env['hr.job'].create({
            'name': 'Test job',
            'default_contract_id': cls.default_contract.id,
        })

        cls.company_id = cls.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': cls.env.ref('base.be').id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'email': 'test_employee@test.example.com',
            'name': 'Test Employee',
            'work_email': 'test_employee@test.example.com',
            'job_id': cls.job.id,
            'company_id': cls.company_id.id,
        })
        cls.employee.user_id.write({
            'password': "employee_password",
            'partner_id': cls.env['res.partner'].create({
                'name': 'Laurie Poiret',
                'street': '58 rue des Wallons',
                'city': 'Louvain-la-Neuve',
                'zip': '1348',
                'country_id': cls.env.ref("base.be").id,
                'phone': '+0032476543210',
                'email': 'laurie.poiret@example.com',
                'company_id': cls.company_id.id,
            }).id,
            'company_id': cls.company_id.id,
            'company_ids': [Command.link(cls.company_id.id)],
        })

        with file_open('hr_contract_salary/static/src/demo/employee_contract.pdf', "rb") as f:
            cls.pdf_content = f.read()

        attachment = cls.env['ir.attachment'].create({
            'type': 'binary',
            'raw': cls.pdf_content,
            'name': 'test_employee_contract.pdf',
        })

        cls.template = cls.env['sign.template'].create({
            'attachment_id': attachment.id,
            'sign_item_ids': [
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_text').id,
                    'name': 'employee_id.name',
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 1,
                    'posX': 0.273,
                    'posY': 0.158,
                    'width': 0.150,
                    'height': 0.015,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_date').id,
                    'name': False,
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 1,
                    'posX': 0.707,
                    'posY': 0.158,
                    'width': 0.150,
                    'height': 0.015,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_text').id,
                    'name': 'employee_id.private_city',
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 1,
                    'posX': 0.506,
                    'posY': 0.184,
                    'width': 0.150,
                    'height': 0.015,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_text').id,
                    'name': 'employee_id.private_country_id.name',
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 1,
                    'posX': 0.663,
                    'posY': 0.184,
                    'width': 0.150,
                    'height': 0.015,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_text').id,
                    'name': 'employee_id.private_street',
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 1,
                    'posX': 0.349,
                    'posY': 0.184,
                    'width': 0.150,
                    'height': 0.015,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_signature').id,
                    'name': False,
                    'required': True,
                    'responsible_id': cls.env.ref('hr_contract_sign.sign_item_role_job_responsible').id,
                    'page': 2,
                    'posX': 0.333,
                    'posY': 0.575,
                    'width': 0.200,
                    'height': 0.050,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_signature').id,
                    'name': False,
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 2,
                    'posX': 0.333,
                    'posY': 0.665,
                    'width': 0.200,
                    'height': 0.050,
                }),
                Command.create({
                    'type_id': cls.env.ref('sign.sign_item_type_date').id,
                    'name': False,
                    'required': True,
                    'responsible_id': cls.env.ref('sign.sign_item_role_employee').id,
                    'page': 2,
                    'posX': 0.665,
                    'posY': 0.694,
                    'width': 0.150,
                    'height': 0.015,
                }),
            ]
        })

    @mute_logger('odoo.http')
    def test_submit_salary_package(self):
        # Create an offer for an applicant
        contract = self.env['hr.contract'].create({
            'name': "Test Contract",
            'wage': 1000,
            'structure_type_id': self.structure_type.id,
            'sign_template_id': self.template.id,
            'contract_update_template_id': self.template.id,
            'hr_responsible_id': self.env.ref('base.user_admin').id,
        })
        salary_offer = self.env['hr.contract.salary.offer'].create([{
            'contract_template_id': self.job.default_contract_id.id,
            'employee_contract_id': contract.id,
            # 'employee_id': self.employee.id,
        }])

        data = {
            "params": {
                "offer_id": salary_offer.id,
                "benefits": {
                    'contract': {
                        'wage': 1000,
                        'final_yearly_costs': 1000,
                    },
                    'employee': {
                        'name': 'New Employee',
                        'private_email': 'new_employee@test.example.com',
                        'employee_job_id': None,
                        'department_id': None,
                        'job_title': None,
                        'private_city': "Louvain-La-Neuve",
                        'private_country_id': self.env.ref("base.be").id,
                        'private_street': "58 rue des Wallons",
                    },
                    'address': {},
                    'bank_account': {},
                },
            },
        }

        res = self.url_open("/salary_package/submit", data=json.dumps(data), headers={"Content-Type": "application/json"})
        content = json.loads(res.content)
        self.assertIn('result', content)

        request_id = self.env['sign.request'].browse(content['result']['request_id'])
        contract_id = self.env['hr.contract'].browse(content['result']['new_contract_id'])
        self.assertTrue(request_id)
        self.assertTrue(contract_id)
        self.assertEqual(contract_id.employee_id.private_city, "Louvain-La-Neuve")
        self.assertEqual(contract_id.employee_id.private_country_id.id, self.env.ref("base.be").id)
        self.assertEqual(contract_id.employee_id.private_street, "58 rue des Wallons")

        self.assertEqual(
            {
                item_value.sign_item_id.name: item_value.value
                for item_value in request_id.request_item_ids.sign_item_value_ids
            },
            {
                "employee_id.name": "New Employee",
                "employee_id.private_city": "Louvain-La-Neuve",
                "employee_id.private_country_id.name": "Belgium",
                "employee_id.private_street": "58 rue des Wallons",
            },
        )

    @mute_logger('odoo.http')
    def test_submit_salary_package_employee(self):
        # Create an offer for an applicant
        contract = self.env['hr.contract'].create({
            'name': "Test Contract",
            'wage': 1000,
            'structure_type_id': self.structure_type.id,
            'sign_template_id': self.template.id,
            'contract_update_template_id': self.template.id,
            'hr_responsible_id': self.env.ref('base.user_admin').id,
            'employee_id': self.employee.id,
        })
        salary_offer = self.env['hr.contract.salary.offer'].create([{
            'contract_template_id': self.job.default_contract_id.id,
            'employee_contract_id': contract.id,
            'employee_id': self.employee.id,
        }])
        self.employee.user_id = self.env['res.users'].create({
            'name': "foo",
            'login': "foo",
            'email': "foo@bar.com",
            'password': "foopassword",
        })

        data = {
            "params": {
                "offer_id": salary_offer.id,
                "benefits": {
                    'contract': {
                        'wage': 1000,
                        'final_yearly_costs': 1000,
                    },
                    'employee': {
                        'name': 'New Employee',
                        'private_email': 'new_employee@test.example.com',
                        'employee_job_id': None,
                        'department_id': None,
                        'job_title': None,
                        'private_city': "Louvain-La-Neuve",
                        'private_country_id': self.env.ref("base.be").id,
                        'private_street': "58 rue des Wallons",
                    },
                    'address': {},
                    'bank_account': {},
                },
            },
        }

        self.authenticate("foo", "foopassword")
        res = self.url_open("/salary_package/submit", data=json.dumps(data), headers={"Content-Type": "application/json"})
        content = json.loads(res.content)
        self.assertIn('result', content)

        request_id = self.env['sign.request'].browse(content['result']['request_id'])
        contract_id = self.env['hr.contract'].browse(content['result']['new_contract_id'])
        self.assertTrue(request_id)
        self.assertTrue(contract_id)
        self.assertEqual(contract_id.employee_id.private_city, "Louvain-La-Neuve")
        self.assertEqual(contract_id.employee_id.private_country_id.id, self.env.ref("base.be").id)
        self.assertEqual(contract_id.employee_id.private_street, "58 rue des Wallons")

        self.assertEqual(
            {
                item_value.sign_item_id.name: item_value.value
                for item_value in request_id.request_item_ids.sign_item_value_ids
            },
            {
                "employee_id.name": "New Employee",
                "employee_id.private_city": "Louvain-La-Neuve",
                "employee_id.private_country_id.name": "Belgium",
                "employee_id.private_street": "58 rue des Wallons",
            },
        )

    def test_sign_item_access(self):
        hradmin, hruser = self.env['res.users'].create([{
            'name': "foo",
            'login': "foo",
            'email': "foo@bar.com",
            'groups_id': [Command.set([self.env.ref('hr_contract.group_hr_contract_manager').id])],
        }, {
            'name': "bar",
            'login': "bar",
            'email': "bar@foo.com",
            'groups_id': [Command.set([
                self.env.ref('sign.group_sign_manager').id,
                self.env.ref('hr_contract.group_hr_contract_employee_manager').id,
            ])],
        }])

        HRSignItem = self.env['sign.item'].with_user(hradmin)
        UserSignItem = self.env['sign.item'].with_user(hruser)
        values = {
            'template_id': self.template.id,
            'type_id': self.env.ref('sign.sign_item_type_text').id,
            'required': True,
            'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
            'page': 1,
            'posX': 0.273,
            'posY': 0.158,
            'width': 0.150,
            'height': 0.015,
        }

        self.template.user_id = hradmin
        # HR has access to the user's private information
        item = HRSignItem.create({'name': 'employee_id.private_street', **values})
        self.assertEqual(item.name, 'employee_id.private_street')

        # Field with a group
        item = HRSignItem.create({'name': 'contracts_count', **values})
        self.assertEqual(item.name, 'contracts_count')

        self.template.user_id = hruser
        # But regular users don't
        item = UserSignItem.create({'name': 'employee_id.private_street', **values})
        self.assertEqual(item.name, '')

        # Accessible fields through an unaccessible model should not work
        item = UserSignItem.create({'name': 'employee_id.user_id.name', **values})
        self.assertEqual(item.name, '')

        # But access to normal fields should work
        item = UserSignItem.create({'name': 'name', **values})
        self.assertEqual(item.name, 'name')

        # Non-field should remain as-is
        item = UserSignItem.create({'name': 'Signature', **values})
        self.assertEqual(item.name, 'Signature')

    def _create_sign_values(self, sign_item_ids, role_id):
        return {
            str(sign_id): 'a'
            for sign_id in sign_item_ids.filtered(
                lambda r: not r.responsible_id or r.responsible_id.id == role_id
            ).mapped('id')
        }

    @mute_logger('odoo.http')
    def test_employee_work_email_should_not_be_updated(self):
        # In any case employee work email should not be updated
        contract = self.env['hr.contract'].create({
            'name': 'Test Contract',
            'wage': 1000,
            'structure_type_id': self.structure_type.id,
            'sign_template_id': self.template.id,
            'contract_update_template_id': self.template.id,
            'hr_responsible_id': self.env.ref('base.user_admin').id,
            'employee_id': self.employee.id,
        })
        salary_offer = self.env['hr.contract.salary.offer'].create({
            'contract_template_id': self.job.default_contract_id.id,
            'employee_contract_id': contract.id,
            'employee_id': self.employee.id,
            'applicant_id': self.env['hr.applicant'].create({
                'candidate_id': self.env['hr.candidate'].create({
                    'partner_id': self.env.ref('base.res_partner_12').id,
                }).id,
            }).id,
        })
        self.employee.user_id = self.env['res.users'].create({
            'name': "foo",
            'login': "foo",
            'email': "foo@bar.com",
            'password': "foopassword",
        })
        self.assertEqual(self.employee.work_email, 'foo@bar.com')
        data = {
            'params': {
                'offer_id': salary_offer.id,
                'benefits': {
                    'contract': {
                        'wage': 1000,
                        'final_yearly_costs': 1000,
                    },
                    'employee': {
                        'name': 'New Employee',
                        'private_email': 'new_employee1111@test.example.com',
                        'employee_job_id': None,
                        'department_id': None,
                        'job_title': None,
                        'private_city': 'Louvain-La-Neuve',
                        'private_country_id': self.env.ref('base.be').id,
                        'private_street': '58 rue des Wallons',
                    },
                    'address': {},
                    'bank_account': {},
                },
            },
        }

        self.authenticate('foo', 'foopassword')
        res = self.url_open('/salary_package/submit', data=json.dumps(data), headers={'Content-Type': 'application/json'})
        content = json.loads(res.content)
        self.assertIn('result', content)
        self.assertEqual(self.employee.work_email, 'foo@bar.com')

        sign_request = self.env['sign.request'].browse(content['result']['request_id'])
        sign_request.template_id.sign_item_ids.write({'required': False})
        sign_data = {
            'signature': self._create_sign_values(
                sign_request.template_id.sign_item_ids,
                self.env.ref('sign.sign_item_role_employee').id,
            )
        }
        sign_res = self.url_open(
            '/sign/sign/%d/%s' % (sign_request.id, content['result']['token']),
            data=json.dumps(sign_data),
            headers={'Content-Type': 'application/json'},
        )
        self.assertIn('result', json.loads(sign_res.content))
        self.assertEqual(self.employee.work_email, 'foo@bar.com')
