from odoo.addons.test_discuss_full.tests.test_performance import TestDiscussFullPerformance

old_method = TestDiscussFullPerformance._get_init_messaging_result


def _get_init_messaging_result(self):
    res = old_method(self)
    for channel in res['channels']:
        if not channel['channel']['channel_type'] == 'livechat':
            continue
        for channel_member in channel['channel']['channelMembers'][0][1]:
            channel_member['persona']['partner']['is_bot'] = False
    return res

def _get_query_count(self):
    return 79


TestDiscussFullPerformance._get_init_messaging_result = _get_init_messaging_result
TestDiscussFullPerformance._get_query_count = _get_query_count
