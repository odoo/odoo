# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.bus.models.bus import BusBus


@tagged('-at_install', 'post_install')
class TestCollaborationBus(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='collab_user', groups='base.group_user,base.group_system')
        cls.partner = cls.env['res.partner'].create({'name': 'Collab Partner'})

    def _broadcast(self, bus_data):
        self.authenticate('collab_user', 'collab_user')
        with patch.object(BusBus, '_sendone') as sendone:
            self.make_jsonrpc_request('/html_editor/bus_broadcast', {
                'model_name': 'res.partner',
                'field_name': 'comment',
                'res_id': self.partner.id,
                'bus_data': bus_data,
            })
        sendone.assert_called_once()
        return sendone.call_args.args[0]

    def test_directed_message_goes_to_peer_channel(self):
        channel = self._broadcast({'notificationName': 'rtc_signal_description', 'toPeerId': '12345'})
        self.assertEqual(
            channel,
            (self.env.cr.dbname, 'editor_collaboration', 'res.partner', 'comment', self.partner.id, '12345'),
        )

    def test_broadcast_message_goes_to_shared_channel(self):
        channel = self._broadcast({'notificationName': 'ptp_join'})
        self.assertEqual(
            channel,
            (self.env.cr.dbname, 'editor_collaboration', 'res.partner', 'comment', self.partner.id),
        )
