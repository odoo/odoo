# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp.tests.common import WhatsAppCommon


class WhatsAppFullCase(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # base test records
        country_be_id = cls.env.ref('base.be').id
        cls.test_partner = cls.env['res.partner'].create({
            'country_id': country_be_id,
            'email': 'whatsapp.customer@test.example.com',
            'mobile': '0485001122',
            'name': 'WhatsApp Customer',
            'phone': '0485221100',
        })
        cls.test_base_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': country_be_id,
                'name': "Test <b>Without Partner</b>r",
                'phone': "+32499123456",
            }, {
                'country_id': country_be_id,
                'customer_id': cls.test_partner.id,
                'name': "Test <b>With partner</b>",
            }
        ])
        cls.test_base_record_nopartner, cls.test_base_record_partner = cls.test_base_records

        # template on base wa model
        cls.whatsapp_template = cls.env['whatsapp.template'].create({
            'body': 'Hello World',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'WhatsApp Template',
            'template_name': 'whatsapp_template',  # not computed because pre-approved
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
        })

        # test report records
        cls.test_wa_base_report = cls.env['ir.actions.report'].create({
            "model": "whatsapp.test.base",
            "name": "Test Report",
            "print_report_name": "'TestReport for %s' % object.name",
            "report_type": "qweb-pdf",
            "report_name": "test_whatsapp.whatsapp_base_template_report",
        })
        cls.test_wa_base_report_view = cls.env['ir.ui.view'].create({
            "arch_db": """<div><p t-foreach="docs" t-as="doc">External report for <t t-out="doc.name"/></p></div>""",
            "key": "test_whatsapp.whatsapp_base_template_report",
            "name": "test_whatsapp.whatsapp_base_template_report",
            "type": "qweb",
        })
        cls.env["ir.model.data"].create({
            "model": "ir.ui.view",
            "module": "test_whatsapp",
            "name": "whatsapp_base_template_report",
            "res_id": cls.test_wa_base_report_view.id,
        })

        cls.env.flush_all()
