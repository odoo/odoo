# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests.common import SMSCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSMSComposerUI(SMSCommon):

    def test_sms_composer_template_tour(self):
        """ Template selector of SMS composer: select a template, manage
        templates (SMS ones, not mail ones). """
        self.env['sms.template'].create({
            'body': 'Hello {{ object.name }}',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'Test SMS template',
        })
        partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'name': 'Jane',
            'phone': '+32 456 00 11 22',
        })
        self.start_tour(f'/odoo/res.partner/{partner.id}', 'sms_composer_template_tour', login=self.user_employee.login)
