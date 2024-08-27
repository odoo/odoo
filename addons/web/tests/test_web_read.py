from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.tests.common import tagged
from odoo import Command


@tagged("post_install", "-at_install")
class TestWebRead(SavepointCaseWithUserDemo):

    def test_web_read_x2many_with_archived_records(self):
        self._load_partners_set()
        Partner = self.env["res.partner"]
        vals = {
            "name": "OpenERP Test",
            "category_id": [Command.set([self.partner_category.id])],
            "child_ids": [
                Command.create(
                    {
                        "name": "address of OpenERP Test",
                        "country_id": self.ref("base.be"),
                        "active": False,
                    }
                )
            ],
        }
        test_partner = Partner.create(vals)
        web_partner = test_partner.web_read(
            specification={
                "child_ids": {"context": {"active_test": False}, "fields": {"id": {}}},
                "category_id": {
                    "context": {"active_test": False},
                    "fields": {"id": {}},
                },
            }
        )[0]
        self.assertTrue(web_partner["category_id"], "Record not Found with category.")

        # testing for one2many field with country Belgium and active=False
        self.assertTrue(
            web_partner["child_ids"],
            "Record not Found with country Belgium and active False.",
        )
