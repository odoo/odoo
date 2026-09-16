from odoo.tests.common import TransactionCase, new_test_user


class TestResPartner(TransactionCase):
    def test_meeting_count(self):
        test_user = new_test_user(
            self.env,
            login="test_user",
            groups="base.group_user, base.group_partner_manager",
        )
        Partner = self.env["res.partner"].with_user(test_user)
        Event = self.env["calendar.event"].with_user(test_user)

        # Partner hierarchy
        #     1       5
        #    /|
        #   2 3
        #     |
        #     4

        test_partner_1 = Partner.create({"name": "test_partner_1"})
        test_partner_2 = Partner.create(
            {"name": "test_partner_2", "parent_id": test_partner_1.id}
        )
        test_partner_3 = Partner.create(
            {"name": "test_partner_3", "parent_id": test_partner_1.id}
        )
        test_partner_4 = Partner.create(
            {"name": "test_partner_4", "parent_id": test_partner_3.id}
        )
        test_partner_5 = Partner.create({"name": "test_partner_5"})
        test_partner_6 = Partner.create({"name": "test_partner_6"})
        test_partner_7 = Partner.create(
            {"name": "test_partner_7", "parent_id": test_partner_6.id}
        )

        Event.create(
            {
                "name": "event_1",
                "partner_ids": [
                    (
                        6,
                        0,
                        [
                            test_partner_1.id,
                            test_partner_2.id,
                            test_partner_3.id,
                            test_partner_4.id,
                        ],
                    )
                ],
            }
        )
        Event.create(
            {
                "name": "event_2",
                "partner_ids": [(6, 0, [test_partner_1.id, test_partner_3.id])],
            }
        )
        Event.create(
            {
                "name": "event_2",
                "partner_ids": [(6, 0, [test_partner_2.id, test_partner_3.id])],
            }
        )
        Event.create(
            {
                "name": "event_3",
                "partner_ids": [(6, 0, [test_partner_3.id, test_partner_4.id])],
            }
        )
        Event.create({"name": "event_4", "partner_ids": [(6, 0, [test_partner_1.id])]})
        Event.create({"name": "event_5", "partner_ids": [(6, 0, [test_partner_3.id])]})
        Event.create({"name": "event_6", "partner_ids": [(6, 0, [test_partner_4.id])]})
        Event.create({"name": "event_7", "partner_ids": [(6, 0, [test_partner_5.id])]})
        Event.create(
            {
                "name": "event_8",
                "partner_ids": [(6, 0, [test_partner_5.id, test_partner_7.id])],
            }
        )

        # Test rule to see if ir.rules are applied
        calendar_event_model_id = self.env["ir.model"]._get("calendar.event").id
        self.env["ir.rule"].create(
            {
                "name": "test_rule",
                "model_id": calendar_event_model_id,
                "domain_force": [("name", "not in", ["event_9", "event_10"])],
                "perm_read": True,
                "perm_create": False,
                "perm_write": False,
            }
        )
        # create generally requires read -> prevented by above test rule
        Event.sudo().create(
            {
                "name": "event_9",
                "partner_ids": [(6, 0, [test_partner_2.id, test_partner_3.id])],
            }
        )

        Event.sudo().create(
            {"name": "event_10", "partner_ids": [(6, 0, [test_partner_5.id])]}
        )

        self.assertEqual(test_partner_1.meeting_count, 7)
        self.assertEqual(test_partner_2.meeting_count, 2)
        self.assertEqual(test_partner_3.meeting_count, 6)
        self.assertEqual(test_partner_4.meeting_count, 3)
        self.assertEqual(test_partner_5.meeting_count, 2)
        self.assertEqual(test_partner_6.meeting_count, 1)
        self.assertEqual(test_partner_7.meeting_count, 1)

    def test_merging_partners_repoints_the_events_that_document_the_source(self):
        Partner = self.env["res.partner"]
        src = Partner.create({"name": "merge src", "email": "merge@example.com"})
        dst = Partner.create({"name": "merge dst", "email": "merge@example.com"})
        event = self.env["calendar.event"].create(
            {
                "name": "about the source",
                "start": "2026-01-05 09:00:00",
                "stop": "2026-01-05 10:00:00",
                "res_model_id": self.env["ir.model"]._get_id("res.partner"),
                "res_id": src.id,
            }
        )
        self.env.flush_all()

        self.env["base.partner.merge.automatic.wizard"].create({})._merge(
            [src.id, dst.id], dst
        )
        self.env.invalidate_all()

        self.assertFalse(src.exists())
        self.assertEqual(
            (event.res_model, event.res_id),
            ("res.partner", dst.id),
            "the registry finds calendar.event's stored reference pair on its "
            "own; no module has to name it",
        )
