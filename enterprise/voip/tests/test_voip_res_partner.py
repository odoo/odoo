from odoo.tests import common, tagged


@tagged("-at_install", "post_install")
class TestVoipResPartner(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.min_length = cls.env["res.partner"]._phone_search_min_length
        cls.partner1 = cls.env["res.partner"].create({
            "name": "Partner 1",
            "phone": "1" * (cls.min_length + 1),
        })
        cls.partner2 = cls.env["res.partner"].create({
            "name": "No matched name",
            "phone": "2" * (cls.min_length + 1),
            "email": "partner2@example.com",
        })
        cls.partner3 = cls.env["res.partner"].create({
            "name": "No matched name, no email",
            "phone": "3" * (cls.min_length + 1),
        })
        cls.partner4 = cls.env["res.partner"].create({
            "name": "partner 4",
            "phone": False,
            "mobile": False,
            "email": "partner4@example.com",
        })
        cls.partner5 = cls.env["res.partner"].create({
            "name": "partner 5",
            "phone": False,
            "mobile": "5" * (cls.min_length + 1),
            "email": "partner5@example.com",
        })

    def assertIdInStoreData(self, id, store_data):
        ids = [record['id'] for record in store_data]
        self.assertIn(id, ids)

    def assertIdNotInStoreData(self, id, store_data):
        ids = [record['id'] for record in store_data]
        self.assertNotIn(id, ids)

    def test_voip_get_contacts_search_by_name_or_email(self):
        """Test that partners are searched by name and email. Only partners with phone or mobile are returned."""
        store_data = self.env["res.partner"].get_contacts(
            offset=0,
            limit=10,
            search_terms="partner",
        )
        self.assertIdInStoreData(self.partner1.id, store_data)
        self.assertIdInStoreData(self.partner2.id, store_data)
        self.assertIdInStoreData(self.partner5.id, store_data)
        self.assertIdNotInStoreData(self.partner3.id, store_data)
        self.assertIdNotInStoreData(self.partner4.id, store_data)

    def test_voip_get_contacts_search_by_phone(self):
        store_data = self.env["res.partner"].get_contacts(
            offset=0,
            limit=10,
            search_terms="3" * self.min_length,
        )
        self.assertIdInStoreData(self.partner3.id, store_data)
        self.assertIdNotInStoreData(self.partner1.id, store_data)
        self.assertIdNotInStoreData(self.partner2.id, store_data)
        self.assertIdNotInStoreData(self.partner5.id, store_data)

    def test_voip_get_contacts_search_by_mobile(self):
        store_data = self.env["res.partner"].get_contacts(
            offset=0,
            limit=10,
            search_terms="5" * self.min_length,
        )
        self.assertIdInStoreData(self.partner5.id, store_data)
        self.assertIdNotInStoreData(self.partner1.id, store_data)
        self.assertIdNotInStoreData(self.partner2.id, store_data)
        self.assertIdNotInStoreData(self.partner3.id, store_data)
