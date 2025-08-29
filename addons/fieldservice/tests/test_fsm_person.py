# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class FSMPerson(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Worker = cls.env["fsm.person"]
        cls.LocationWorker = cls.env["fsm.location.person"]

    def test_fsm_person(self):
        # Create a person
        test_worker_one = self.Worker.create({"name": "Worker One"})
        self.assertTrue(test_worker_one.fsm_person)
        # Test toggle_active
        test_worker_one.toggle_active()
        self.assertTrue(
            test_worker_one.partner_id.active,
            "Partner related to FSM Person should remain active",
        )
        test_worker_one.partner_id.toggle_active()
        test_worker_one.toggle_active()
        self.assertTrue(
            test_worker_one.partner_id.active,
            "Activating FSM Person must make related partner active",
        )

    def test_fsm_person_search(self):
        # Setup locations
        location_1 = self.env.ref("fieldservice.location_1")
        location_2 = self.env.ref("fieldservice.location_2")
        location_3 = self.env.ref("fieldservice.location_3")
        # Setup Persons
        person_1 = self.env.ref("fieldservice.person_1")
        person_2 = self.env.ref("fieldservice.person_2")
        person_3 = self.env.ref("fieldservice.person_3")
        # Setup Location Persons
        self.LocationWorker.create(
            {
                "location_id": location_1.id,
                "person_id": person_1.id,
            }
        )
        self.LocationWorker.create(
            {
                "location_id": location_2.id,
                "person_id": person_2.id,
            }
        )
        self.LocationWorker.create(
            {
                "location_id": location_3.id,
                "person_id": person_3.id,
            }
        )
        # Test search using a location ID
        search_domain = [("location_ids", "=", location_2.id)]
        workers = self.Worker.search(search_domain)
        self.assertEqual(workers.id[0], person_2.id)
        # Test search using a location name
        search_domain = [("location_ids", "=", "Location")]
        workers = self.Worker.search(search_domain)
        self.assertEqual(len(workers), 3, "Incorrect search number result")
