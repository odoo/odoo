from odoo.addons.mail.tools.discuss import Store
from odoo.tests import common, tagged


@tagged("voip", "post_install", "-at_install")
class TestVoipMultipleProviders(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider_1 = cls.env["voip.provider"].create({
            "name": "demo",
            "mode": "demo",
        })
        cls.provider_2 = cls.env["voip.provider"].create({
            "name": "prod",
            "mode": "prod",
            "pbx_ip": "localhost",
            "ws_server": "ws://localhost",
        })

    def test_voip_init_messaging(self):
        user = self.env.user
        user.voip_provider_id = self.provider_1
        store = Store()
        user._init_store_data(store)
        data = store.get_result()
        self.assertEqual(data["Store"]["voipConfig"]["mode"], self.provider_1.mode)
        self.assertEqual(data["Store"]["voipConfig"]["pbxAddress"], self.provider_1.pbx_ip)
        self.assertEqual(data["Store"]["voipConfig"]["webSocketUrl"], self.provider_1.ws_server)

        user.voip_provider_id = self.provider_2
        store = Store()
        user._init_store_data(store)
        data = store.get_result()
        self.assertEqual(data["Store"]["voipConfig"]["mode"], self.provider_2.mode)
        self.assertEqual(data["Store"]["voipConfig"]["pbxAddress"], self.provider_2.pbx_ip)
        self.assertEqual(data["Store"]["voipConfig"]["webSocketUrl"], self.provider_2.ws_server)
