# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install', 'assets_bundle')
class BusWebTests(odoo.tests.HttpCase):

    def test_bundle_sends_bus(self):
        """
        Tests two things:
        - Messages are posted to the bus when assets change
          i.e. their hash has been recomputed and differ from the attachment's
        - The interface deals with those bus messages by displaying one notification
        """
        # start from a clean slate
        self.env['ir.attachment'].search([('name', 'ilike', 'web.assets_%')]).unlink()
        self.env.registry.clear_cache()

        sendones = []
        def patched_sendone(self, channel, notificationType, message):
            """ Control API and number of messages posted to the bus linked to
            bundle_changed events """
            if notificationType == 'bundle_changed':
                sendones.append((channel, message))

        self.patch(type(self.env['bus.bus']), '_sendone', patched_sendone)

        self.assertEqual(self.url_open('/web/assets/any/web.assets_web.min.js', allow_redirects=False).status_code, 200)
        self.assertEqual(self.url_open('/web/assets/any/web.assets_web.min.css', allow_redirects=False).status_code, 200)
        self.assertEqual(self.url_open('/web/assets/any/web.assets_backend.min.js', allow_redirects=False).status_code, 200)
        self.assertEqual(self.url_open('/web/assets/any/web.assets_backend.min.css', allow_redirects=False).status_code, 200)

        # One sendone for each asset bundle and for each CSS / JS
        self.assertEqual(
            len(sendones),
            2,
            'Received %s' % '\n'.join('%s - %s' % (tmp[0], tmp[1]) for tmp in sendones)
        )
        for (channel, message) in sendones:
            self.assertEqual(channel, 'broadcast')
            self.assertEqual(len(message), 1)
            self.assertTrue(isinstance(message.get('server_version'), str))
