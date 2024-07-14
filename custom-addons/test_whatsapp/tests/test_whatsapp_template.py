# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.tests import tagged, users


@tagged('wa_template')
class WhatsAppTemplate(WhatsAppFullCase):

    @users('user_wa_admin')
    def test_template_phone_field_chain(self):
        """ Test "phone_field" being a field chain """
        template = self.env['whatsapp.template'].create({
            'body': 'Hello Phone Field Chain',
            'model_id': self.env['ir.model']._get_id(self.test_base_records._name),
            'name': 'WhatsApp Template',
            'phone_field': 'customer_id.phone',
            'template_name': 'Phone Field Chain',
            'status': 'approved',
            'wa_account_id': self.whatsapp_account.id,
        })

        # record with a partner set
        for test_record in self.test_base_record_nopartner + self.test_base_record_partner:
            with self.subTest(test_record=test_record):
                test_record = test_record.with_env(self.env)
                composer = self._instanciate_wa_composer_from_records(template, test_record)
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()
                if test_record == self.test_base_record_partner:
                    self.assertWAMessage(
                        fields_values={
                            'mobile_number': "0485221100",
                        },
                    )
                # no number found -> no message produced
                else:
                    self.assertFalse(self._new_wa_msg)
