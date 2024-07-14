# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_discuss_full.tests.test_performance import TestDiscussFullPerformance

old_method = TestDiscussFullPerformance._get_init_messaging_result


def _get_init_messaging_result(self):
    res = old_method(self)
    res['current_user_settings'].update({
        'homemenu_config': False,
        'how_to_call_on_mobile': 'ask',
        'external_device_number': False,
        'onsip_auth_username': False,
        'should_call_from_another_device': False,
        'should_auto_reject_incoming_calls': False,
        'voip_secret': False,
        'voip_username': False,
        'is_discuss_sidebar_category_whatsapp_open': True,
    })
    res['voipConfig'] = {
        'mode': 'demo',
        'missedCalls': 0,
        'pbxAddress': "localhost",
        'webSocketUrl': self.env["ir.config_parameter"].sudo().get_param("voip.wsServer", default="ws://localhost"),
    }
    res['hasDocumentsUserGroup'] = False
    res['helpdesk_livechat_active'] = False
    return res


TestDiscussFullPerformance._get_init_messaging_result = _get_init_messaging_result
TestDiscussFullPerformance._query_count += 11
