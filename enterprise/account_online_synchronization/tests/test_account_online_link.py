from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_online_synchronization.tests.common import AccountOnlineSynchronizationCommon


@tagged('post_install', '-at_install')
class TestAccountOnlineLink(AccountOnlineSynchronizationCommon):
    def test_action_new_synchronization(self):
        def _get_latest_link():
            return self.env['account.online.link'].search([], order='create_date, id desc', limit=1)

        def _assert_link_count(count, message):
            self.assertEqual(
                self.env['account.online.link'].search_count([]),
                count,
                message,
            )

        link_count = self.env['account.online.link'].search_count([])

        self.env['account.online.link'].action_new_synchronization()
        link_count += 1
        _assert_link_count(
            link_count,
            "A new account online link should have been created.",
        )

        link = _get_latest_link()
        link['provider_type'] = 'some_provider'
        self.env['account.online.link'].action_new_synchronization()
        link_count += 1
        _assert_link_count(
            link_count,
            "A new account online link should have been created since there are no links without a provider type",
        )

        link = _get_latest_link()
        link['provider_type'] = False
        link['account_online_account_ids'] = [
            Command.create({
                'name': 'Some Account',
            }),
        ]
        self.env['account.online.link'].action_new_synchronization()
        link_count += 1
        _assert_link_count(
            link_count,
            "A new account online link should have been created since there are no links without account_online_account_ids",
        )

        link.action_new_synchronization()
        _assert_link_count(
            link_count,
            "No new account online link should have been created since the recordset contains one",
        )
