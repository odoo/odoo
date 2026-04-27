# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_discuss_full.tests.test_performance import TestDiscussFullPerformance

# Queries for _query_count_init_store:
#   1: _get_default_voip_provider when creating res.users.settings
#   1: voipConfig: missedCalls
TestDiscussFullPerformance._query_count_init_store += 2
TestDiscussFullPerformance._query_count_init_messaging += 0
TestDiscussFullPerformance._query_count_discuss_channels += 0

old_get_init_store_data_result = TestDiscussFullPerformance._get_init_store_data_result


def _get_init_store_data_result(self):
    res = old_get_init_store_data_result(self)
    provider = self.env.ref("voip.default_voip_provider").sudo()
    channel_types_with_seen_infos = res["Store"]["channel_types_with_seen_infos"] + ["whatsapp"]
    res["Store"].update(
        {
            "channel_types_with_seen_infos": sorted(channel_types_with_seen_infos),
            "hasDocumentsUserGroup": False,
            "helpdesk_livechat_active": False,
            "voipConfig": {
                "mode": "demo",
                "missedCalls": 0,
                "pbxAddress": "localhost",
                "webSocketUrl": provider.ws_server or "ws://localhost",
            },
        }
    )
    res["Store"]["settings"].update(
        {
            "homemenu_config": False,
            "how_to_call_on_mobile": "ask",
            "external_device_number": False,
            "onsip_auth_username": False,
            "should_call_from_another_device": False,
            "should_auto_reject_incoming_calls": False,
            "voip_provider_id": (provider.id, provider.name),
            "voip_secret": False,
            "voip_username": False,
            "is_discuss_sidebar_category_whatsapp_open": True,
        }
    )
    return res


TestDiscussFullPerformance._get_init_store_data_result = _get_init_store_data_result
