# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

try:
    import websocket
except ImportError:
    websocket = None

from odoo.http.session import session_store
from odoo.tests import tagged
from odoo.tests.common import HOST, JsonRpcException, new_test_user
from odoo.tools import mute_logger

from odoo.addons.bus.tests.common import BusCase, BusResult, WebsocketCase
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestWebrtcSignal(TestPointOfSaleHttpCommon, BusCase):
    """ The server relays the WebRTC signaling messages on the bus channel of the config. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config._ensure_access_token()
        cls.sdp = {'type': 'offer', 'sdp': 'v=0'}
        cls.answer_sdp = {'type': 'answer', 'sdp': 'v=0'}

    def signal(self, message, config=None):
        config = config or self.main_pos_config
        return self.make_jsonrpc_request('/pos/webrtc/signal', {
            'config_id': config.id,
            'message': message,
        })

    def expected(self, message, config=None):
        config = config or self.main_pos_config
        return BusResult((config, "webrtc"), f"WEBRTC_SIGNAL-{config.id}", message)

    def device_id(self, name, session=None):
        """ The id of a device `name` running in `session` (default: the current one). """
        session = session or self.session
        return f"{name}.{self.env['pos.config']._get_webrtc_session_tag(session.sid)}"

    def test_relay_valid_messages(self):
        """ Announce (broadcast and directed), offer and answer are relayed as is. """
        self.authenticate('pos_user', 'pos_user')
        # Two devices in the same browser (e.g. two tabs) share their session.
        a, b = self.device_id('a'), self.device_id('b')
        messages = [
            {'type': 'announce', 'from': a},
            {'type': 'announce', 'from': b, 'to': a},
            {'type': 'offer', 'from': a, 'to': b, 'attempt': 1, 'sdp': self.sdp},
            {'type': 'answer', 'from': b, 'to': a, 'attempt': 1, 'sdp': self.answer_sdp},
        ]
        for message in messages:
            with self.subTest(type=message['type'], to=message.get('to')):
                with self.assertBus([self.expected(message)]):
                    self.signal(message)

    def test_reject_invalid_messages(self):
        """ An invalid message raises and nothing is sent on the bus. """
        self.authenticate('pos_user', 'pos_user')
        invalid_messages = {
            'not a dict': 'announce',
            'unknown type': {'type': 'bye', 'from': 'a'},
            'no type': {'from': 'a'},
            'no from': {'type': 'announce'},
            'from not a string': {'type': 'announce', 'from': 42},
            'to not a string': {'type': 'announce', 'from': 'a', 'to': 42},
            'offer without sdp': {'type': 'offer', 'from': 'a', 'to': 'b'},
            'answer without sdp': {'type': 'answer', 'from': 'b', 'to': 'a'},
            'sdp not a dict': {'type': 'offer', 'from': 'a', 'to': 'b', 'sdp': 'v=0'},
        }
        for case, message in invalid_messages.items():
            with self.subTest(case=case):
                with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
                    self.signal(message)
                self.assertEqual(error.exception.args[0], 'odoo.exceptions.ValidationError')

    def test_reject_malformed_messages(self):
        """ A message that doesn't follow the protocol exactly raises and nothing is sent on the bus. """
        self.authenticate('pos_user', 'pos_user')
        long_id = 'x' * 65

        def offer(**values):
            return {'type': 'offer', 'from': 'a', 'to': 'b', 'attempt': 1, 'sdp': self.sdp, **values}

        def answer(**values):
            return {'type': 'answer', 'from': 'b', 'to': 'a', 'attempt': 1, 'sdp': self.answer_sdp, **values}

        invalid_messages = {
            # Only an announce can be sent to every device.
            'offer without to': {k: v for k, v in offer().items() if k != 'to'},
            'answer without to': {k: v for k, v in answer().items() if k != 'to'},
            # Ids.
            'empty from': {'type': 'announce', 'from': ''},
            'empty to': {'type': 'announce', 'from': 'a', 'to': ''},
            'from too long': {'type': 'announce', 'from': long_id},
            'to too long': {'type': 'announce', 'from': 'a', 'to': long_id},
            'sent to itself': {'type': 'announce', 'from': 'a', 'to': 'a'},
            # Attempt number.
            'offer without attempt': {k: v for k, v in offer().items() if k != 'attempt'},
            'answer without attempt': {k: v for k, v in answer().items() if k != 'attempt'},
            'attempt not an integer': offer(attempt='1'),
            'attempt a boolean': offer(attempt=True),
            'attempt zero': offer(attempt=0),
            'attempt negative': answer(attempt=-1),
            'announce with attempt': {'type': 'announce', 'from': 'a', 'attempt': 1},
            # Session description.
            'announce with sdp': {'type': 'announce', 'from': 'a', 'sdp': self.sdp},
            'sdp without sdp': offer(sdp={'type': 'offer'}),
            'sdp without type': offer(sdp={'sdp': 'v=0'}),
            'sdp text not a string': offer(sdp={'type': 'offer', 'sdp': 42}),
            'sdp with another key': offer(sdp={**self.sdp, 'extra': 'x'}),
            'offer with an answer sdp': offer(sdp=self.answer_sdp),
            'answer with an offer sdp': answer(sdp=self.sdp),
            # Unknown keys.
            'announce with an unknown key': {'type': 'announce', 'from': 'a', 'group': 'x'},
            'offer with an unknown key': offer(uid=2),
        }
        for case, message in invalid_messages.items():
            with self.subTest(case=case):
                with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
                    self.signal(message)
                self.assertEqual(error.exception.args[0], 'odoo.exceptions.ValidationError')

    def test_message_size(self):
        """ A message of up to 64 KB is relayed, a bigger one raises and nothing is sent on the bus. """
        self.authenticate('pos_user', 'pos_user')
        # A real session description, with its candidates, is a few KB.
        message = {
            'type': 'offer', 'from': self.device_id('a'), 'to': 'b', 'attempt': 1,
            'sdp': {'type': 'offer', 'sdp': 'v' * 60_000},
        }
        with self.assertBus([self.expected(message)]):
            self.signal(message)

        message['sdp']['sdp'] = 'v' * 70_000
        with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
            self.signal(message)
        self.assertEqual(error.exception.args[0], 'odoo.exceptions.ValidationError')

    @mute_logger('odoo.http')
    def test_reject_forged_sender(self):
        """ A device can only send messages from an id of its own session: another
        user of the config can't pretend to be it, even with its id. """
        self.authenticate('pos_user', 'pos_user')
        victim = self.device_id('victim')
        cases = {
            # Seen on the channel of the config, used from another session.
            'id of another user': ('pos_admin', lambda: victim),
            'id of another session of the same user': ('pos_user', lambda: victim),
            'id without session tag': ('pos_user', lambda: 'victim'),
            'own tag not at the end': ('pos_user', lambda: f"{self.device_id('x')}.victim"),
        }
        for case, (login, sender) in cases.items():
            with self.subTest(case=case):
                self.authenticate(login, login)
                with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
                    self.signal({'type': 'announce', 'from': sender()})
                self.assertEqual(error.exception.args[0], 'odoo.exceptions.AccessError')

    def test_sender_id_survives_session_rotation(self):
        """ The session id is rotated every few hours while the PoS stays open: the
        device keeps its id, and can still send messages. """
        session = self.authenticate('pos_user', 'pos_user')
        a = self.device_id('a')
        old_sid = session.sid
        # What the server does to a session older than SESSION_ROTATION_INTERVAL.
        session_store().rotate(session, self.env, soft=True)
        self.opener.cookies.set('session_id', session.sid, domain=HOST)
        self.assertNotEqual(session.sid, old_sid)
        message = {'type': 'announce', 'from': a}
        with self.assertBus([self.expected(message)]):
            self.signal(message)

    @mute_logger('odoo.http')
    def test_access_rights(self):
        """ Only users who can read the config can signal on its channel. """
        new_test_user(self.env, login='no_pos', password='no_pos', groups='base.group_user')
        self.authenticate('no_pos', 'no_pos')
        with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
            self.signal({'type': 'announce', 'from': 'a'})
        self.assertEqual(error.exception.args[0], 'odoo.exceptions.AccessError')

        self.authenticate(None, None)
        with self.assertBus([]), self.assertRaises(JsonRpcException) as error:
            self.signal({'type': 'announce', 'from': 'a'})
        self.assertEqual(error.exception.args[0], 'odoo.http.session.SessionExpiredException')

    def test_config_isolation(self):
        """ A message is only sent on the channel of its config. """
        other_config = self.env['pos.config'].create({'name': 'Other shop'})
        other_config._ensure_access_token()
        self.authenticate('pos_user', 'pos_user')
        message = {'type': 'announce', 'from': self.device_id('a')}
        with self.assertBus([self.expected(message)]):
            self.signal(message)
        with self.assertBus([self.expected(message, other_config)]):
            self.signal(message, other_config)


@tagged('post_install', '-at_install')
class TestWebrtcChannel(TestPointOfSaleHttpCommon, WebsocketCase):
    """ The signaling messages contain the network addresses of the devices:
    only the users of the config receive them, not the customer display nor the
    self order, which know the access token of the config. """

    def connect(self, login, channels):
        """ Open a websocket as `login` (None: public user) and subscribe it to `channels`. """
        # Else `authenticate` deletes the session of the previous websocket, which the
        # server then closes.
        self.session = None
        if login:
            session = self.authenticate(login, login)
            ws = self.websocket_connect(cookie=f"session_id={session.sid}")
        else:
            ws = self.websocket_connect()
        # The env of the test runs as a user who can't read the bus.
        self.subscribe(ws, channels, self.env['bus.bus'].sudo()._bus_last_id())
        return ws

    def received_signals(self, ws, timeout):
        """ The WebRTC signaling messages received by `ws` until nothing comes for `timeout` seconds. """
        ws.settimeout(timeout)
        signals = []
        try:
            while True:
                data = ws.recv()
                # Anything but a text frame: the server closed the websocket.
                self.assertTrue(data, "The websocket was closed by the server")
                for notification in json.loads(data):
                    if 'WEBRTC_SIGNAL' in notification['message']['type']:
                        signals.append(notification['message'])
                if signals:
                    return signals
        except websocket.WebSocketTimeoutException:
            return signals

    def test_only_users_of_the_config_receive_the_signals(self):
        """ A user who can read the config receives its signals by asking for its WebRTC
        channel; a public client or a user without access receives nothing, whatever it asks for. """
        config = self.main_pos_config
        config._ensure_access_token()
        private_channel = f"pos.config_webrtc_{config.id}"
        new_test_user(self.env, login='no_pos', password='no_pos', groups='base.group_user')
        device = self.connect('pos_user', [private_channel])
        # The customer display and the self order subscribe to the access token.
        customer_display = self.connect(None, [config.access_token])
        public_asking = self.connect(None, [config.access_token, private_channel])
        no_access = self.connect('no_pos', [config.access_token, private_channel])
        malformed = self.connect('pos_user', [f"pos.config_webrtc_{config.id}x", "pos.config_webrtc_"])

        message = {'type': 'announce', 'from': 'a.tag'}
        config._webrtc_signal(message, sender_tag='tag')
        self.trigger_notification_dispatching()

        self.assertEqual(
            self.received_signals(device, timeout=5),
            [{'type': f"WEBRTC_SIGNAL-{config.id}", 'payload': message}],
        )
        # The notification was dispatched to every websocket at once.
        for name, ws in [
            ('customer display', customer_display),
            ('public client asking for the channel', public_asking),
            ('user without access', no_access),
            ('malformed channel names', malformed),
        ]:
            with self.subTest(client=name):
                self.assertEqual(self.received_signals(ws, timeout=0.5), [])

    def test_other_config_channel(self):
        """ The WebRTC channel of a config doesn't receive the signals of another config. """
        other_config = self.env['pos.config'].create({'name': 'Other shop'})
        device = self.connect('pos_user', [f"pos.config_webrtc_{other_config.id}"])
        other_device = self.connect('pos_user', [f"pos.config_webrtc_{self.main_pos_config.id}"])

        self.main_pos_config._webrtc_signal({'type': 'announce', 'from': 'a.tag'}, sender_tag='tag')
        self.trigger_notification_dispatching()

        self.assertEqual(len(self.received_signals(other_device, timeout=5)), 1)
        self.assertEqual(self.received_signals(device, timeout=0.5), [])


@tagged('post_install', '-at_install')
class TestWebrtcUi(TestPointOfSaleHttpCommon):
    """ Devices of the same PoS, each one in its own browser, connect to each
    other and say "Hi". The ids of the devices are fixed by the tests (see
    `patchWebrtcForTests` in the tours), so that the tours know which one sends
    the offer. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A third cashier, for the tests with three devices.
        cls.pos_user_2 = cls.env['res.users'].create({
            'name': 'Another PoS man',
            'login': 'pos_user_2',
            'password': 'pos_user_2',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
            ],
        })

    def start_devices(self, *devices):
        """ Open the devices in the given order, and run their tours at the same time.

        :param devices: one `(tour_name, device_id, login)` tuple per device
        """
        # Open the session beforehand, so that the devices don't try to open it.
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.main_pos_config.current_session_id.set_opening_control(0, "")
        url = f"{self._get_url()}?debug_webrtc=1"
        self.start_tours(*(
            {
                'url_path': url,
                'tour_name': tour_name,
                'login': login,
                'cookies': {'webrtc_test_id': device_id},
                # Open the next device once this one has announced itself,
                # so that the order of the announces is the order of the devices.
                'ready': f"""odoo.isTourReady({tour_name!r}) && window.posmodel?.webrtc.logger.logs().some(
                    (log) => log.type === "signal" && log.text === "sent announce to all"
                )""",
            }
            for tour_name, device_id, login in devices
        ))

    def test_webrtc_smaller_first(self):
        """ The device with the smaller id is already open when the other one
        announces itself: it sends the offer right away. """
        self.start_devices(
            ('test_webrtc_smaller_first_t1', 'device1', 'pos_user'),
            ('test_webrtc_smaller_first_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_bigger_first(self):
        """ The device with the bigger id is already open when the other one
        announces itself: it announces itself back to the newcomer, which sends
        the offer. """
        self.start_devices(
            ('test_webrtc_bigger_first_t2', 'device2', 'pos_user'),
            ('test_webrtc_bigger_first_t1', 'device1', 'pos_admin'),
        )

    def test_webrtc_three_devices(self):
        """ Three devices: each pair connects once, and each device receives
        the "Hi" of the two other ones. """
        self.start_devices(
            ('test_webrtc_three_t1', 'device1', 'pos_user'),
            ('test_webrtc_three_t2', 'device2', 'pos_admin'),
            ('test_webrtc_three_t3', 'device3', 'pos_user_2'),
        )

    def test_webrtc_leave(self):
        """ A device leaving the PoS (e.g. its tab is closed) says goodbye and
        closes its connections: the other devices remove it from their peers,
        without any signaling nor trying to reconnect to it, and keep talking to
        each other. """
        self.start_devices(
            ('test_webrtc_leave_t1', 'device1', 'pos_user'),
            ('test_webrtc_leave_t2', 'device2', 'pos_admin'),
            ('test_webrtc_leave_t3', 'device3', 'pos_user_2'),
        )

    def test_webrtc_reload(self):
        """ A device reloading its page comes back with a new id: the other
        device ends up with a single peer, the new one (no ghost of the old
        id), and they talk again. """
        self.start_devices(
            ('test_webrtc_reload_t1', 'device1', 'pos_user'),
            ('test_webrtc_reload_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_back_forward_cache(self):
        """ A device leaving its page and coming back to it from the
        back/forward cache closed its connections when leaving: it comes back
        with a new id, announces itself again, and reconnects to the other
        device, which ends up with a single peer. The cache is simulated:
        Chrome never caches the PoS, other browsers might. """
        self.start_devices(
            ('test_webrtc_back_forward_cache_t1', 'device1', 'pos_user'),
            ('test_webrtc_back_forward_cache_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_announce_again_bigger(self):
        """ A connected device with the bigger id announcing itself again
        (e.g. when its websocket reconnects) keeps its connection: the other
        device doesn't send a new offer. """
        self.start_devices(
            ('test_webrtc_announce_again_bigger_t1', 'device1', 'pos_user'),
            ('test_webrtc_announce_again_bigger_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_announce_again_smaller(self):
        """ A connected device with the smaller id announcing itself again
        keeps its connection: the other device doesn't announce itself back,
        which would make the first one send a new offer. """
        self.start_devices(
            ('test_webrtc_announce_again_smaller_t1', 'device1', 'pos_user'),
            ('test_webrtc_announce_again_smaller_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_server_cut(self):
        """ Connected devices cut from the server keep talking to each other.
        Once back, they announce themselves again, and keep their connection. """
        self.start_devices(
            ('test_webrtc_server_cut_t1', 'device1', 'pos_user'),
            ('test_webrtc_server_cut_t2', 'device2', 'pos_admin'),
        )

    def test_webrtc_alone(self):
        """ A device alone announces itself, and has nobody to talk to. """
        self.start_devices(
            ('test_webrtc_alone', 'device1', 'pos_user'),
        )
