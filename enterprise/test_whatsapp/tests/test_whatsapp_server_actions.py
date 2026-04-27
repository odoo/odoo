# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.tests import tagged, users


@tagged('ir_actions')
class WhatsAppServerAction(WhatsAppFullCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_server_action = cls.env['ir.actions.server'].create({
            'name': 'Test Action',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'state': 'whatsapp',
            'wa_template_id': cls.whatsapp_template.id,
        })

    def test_action_whatsapp(self):
        """ Test server action of WhatsApp type using multiple records """
        context = {
            'active_model': 'whatsapp.test.base',
            'active_ids': self.test_base_records.ids,
        }

        with self.with_user('employee'), self.mockWhatsappGateway():
            self.test_server_action.with_context(**context).run()
        self.assertWAMessageFromRecord(self.test_base_record_nopartner, status='outgoing')
        self.assertWAMessageFromRecord(self.test_base_record_partner, status='outgoing')

    @users('admin')
    def test_compute_wa_template_id(self):
        """ Test WhatsApp template drop on state change or model change """
        test_server_action = self.test_server_action
        # Check whatsapp template drop on state change
        test_server_action.state = 'sms'
        self.assertFalse(test_server_action.wa_template_id)

        # Reset server action with whatsapp state
        test_server_action.write({
            'state': 'whatsapp',
            'wa_template_id': self.whatsapp_template.id,
        })

        # Check whatsapp template drop on model change
        test_server_action.model_id = self.env['ir.model']._get_id('res.country')
        self.assertFalse(test_server_action.wa_template_id)
