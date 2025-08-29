# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class Common(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "partner test"})
        cls.location = cls.env["fsm.location"].create(
            {"name": "location test", "owner_id": cls.partner.id}
        )
        cls.project = cls.env["project.project"].create({"name": "project test"})
