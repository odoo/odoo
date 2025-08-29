# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

import requests

from odoo.tests import Form
from odoo.tools import misc

from odoo.addons.base.tests.common import BaseCommon


class TestSign(BaseCommon):
    @classmethod
    def setUpClass(cls):
        cls._super_send = requests.Session.send
        super().setUpClass()
        cls.data = base64.b64encode(
            open(
                misc.file_path(f"{cls.test_module}/tests/empty.pdf"),
                "rb",
            ).read()
        )
        cls.template = cls.env["sign.oca.template"].create(
            {
                "data": cls.data,
                "name": "Demo template",
                "filename": "empty.pdf",
            }
        )
        cls.signer = cls.env["res.partner"].create({"name": "Signer"})
        cls.request = cls.env["sign.oca.request"].create(
            {
                "data": cls.data,
                "name": "Demo template",
                "signer_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.signer.id,
                            "role_id": cls.env.ref("sign_oca.sign_role_customer").id,
                        },
                    )
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})
        cls.partner_child = cls.env["res.partner"].create(
            {"name": "Child partner", "parent_id": cls.partner.id}
        )
        cls.role_customer = cls.env.ref("sign_oca.sign_role_customer")
        cls.role_supervisor = cls.env.ref("sign_oca.sign_role_supervisor")
        cls.role_supervisor.default_partner_id = cls.partner
        cls.role_child_partner = cls.env["sign.oca.role"].create(
            {
                "name": "Child partner",
                "partner_selection_policy": "expression",
                "expression_partner": "{{object.parent_id.id}}",
            }
        )

    def configure_template(self):
        self.template.add_item(
            {
                "field_id": self.env.ref("sign_oca.sign_field_name").id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 10,
                "height": 10,
                "required": True,
            }
        )

    def configure_request(self):
        return self.request.add_item(
            {
                "field_id": self.env.ref("sign_oca.sign_field_name").id,
                "role_id": self.role_customer.id,
                "page": 1,
                "position_x": 10,
                "position_y": 10,
                "width": 10,
                "height": 10,
                "required": True,
            }
        )

    @classmethod
    def _request_handler(cls, s, r, /, **kw):
        """Don't block external requests."""
        return cls._super_send(s, r, **kw)

    def test_template_configuration(self):
        self.assertFalse(self.template.get_info()["items"])
        self.configure_template()
        self.assertTrue(self.template.get_info()["items"])

    def test_template_field_edition(self):
        self.configure_template()
        self.assertEqual(self.template.item_ids.role_id, self.role_customer)
        self.template.set_item_data(
            self.template.item_ids.id,
            {"role_id": self.env.ref("sign_oca.sign_role_employee").id},
        )
        self.assertEqual(
            self.template.item_ids.role_id, self.env.ref("sign_oca.sign_role_employee")
        )

    def test_template_field_delete(self):
        self.configure_template()
        self.assertTrue(self.template.item_ids)
        self.template.delete_item(self.template.item_ids.id)
        self.assertFalse(self.template.item_ids)

    def test_request_configuration(self):
        self.assertFalse(self.request.get_info()["items"])
        self.configure_request()
        self.assertTrue(self.request.get_info()["items"])
        signer_info = self.request.signer_ids.get_info()
        self.assertEqual(signer_info["partner"]["id"], self.signer.id)
        self.assertEqual(signer_info["partner"]["name"], "Signer")

    def test_request_field_edition(self):
        item = self.configure_request()
        self.assertEqual(
            self.request.get_info()["items"][str(item["id"])]["role_id"],
            self.env.ref("sign_oca.sign_role_customer").id,
        )
        self.request.set_item_data(
            str(item["id"]), {"role_id": self.env.ref("sign_oca.sign_role_employee").id}
        )
        self.assertEqual(
            self.request.get_info()["items"][str(item["id"])]["role_id"],
            self.env.ref("sign_oca.sign_role_employee").id,
        )

    def test_request_field_delete(self):
        item = self.configure_request()
        self.assertTrue(self.request.get_info()["items"])
        self.request.delete_item(str(item["id"]))
        self.assertFalse(self.request.get_info()["items"])

    def test_template_generate_without_model_partner_selection_policy_empty(self):
        """Template without model, role with empty partner type option."""
        self.configure_template()
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id
            )
        )
        with f.signer_ids.edit(0) as signer:
            self.assertFalse(signer.partner_id)
            signer.partner_id = self.partner
        action = f.save().generate()
        request = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(len(request.signer_ids), 1)
        self.assertIn(self.partner, request.signer_ids.mapped("partner_id"))

    def test_template_generate_without_model_partner_selection_policy_default(self):
        """Template without model, role with default partner type option."""
        self.configure_template()
        self.template.item_ids.role_id = self.role_supervisor
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id
            )
        )
        action = f.save().generate()
        request = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(len(request.signer_ids), 1)
        self.assertIn(self.partner, request.signer_ids.mapped("partner_id"))

    def test_sign_request_role_with_default(self):
        request_form = Form(self.env["sign.oca.request"])
        with request_form.signer_ids.new() as signer:
            signer.role_id = self.role_supervisor
            self.assertEqual(signer.partner_id, self.partner)

    def test_sign_request_role_with_expression(self):
        request_form = Form(self.env["sign.oca.request"])
        request_form.record_ref = f"{self.partner_child._name},{self.partner_child.id}"
        with request_form.signer_ids.new() as signer:
            signer.role_id = self.role_child_partner
            self.assertEqual(signer.partner_id, self.partner)

    def test_template_generate_multi_partner(self):
        self.configure_template()
        model_res_partner = self.env.ref("base.model_res_partner")
        self.template.model_id = model_res_partner
        self.template.item_ids.role_id = self.role_child_partner
        partner_child_2 = self.env["res.partner"].create(
            {"name": "Child partner extra", "parent_id": self.partner.id}
        )
        wizard_form = Form(
            self.env["sign.oca.template.generate.multi"].with_context(
                default_model="res.partner", active_ids=self.partner.child_ids.ids
            )
        )
        wizard_form.template_id = self.template
        action = wizard_form.save().generate()
        requests = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(len(requests), 2)
        signer_partners = requests.mapped("signer_ids.partner_id")
        self.assertIn(self.partner, signer_partners)
        self.assertNotIn(self.partner_child, signer_partners)
        self.assertNotIn(partner_child_2, signer_partners)

    def test_auto_sign_template(self):
        self.configure_template()
        self.assertEqual(0, self.template.request_count)
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id, default_sign_now=True
            )
        )
        f.save().generate()
        self.assertEqual(1, self.template.request_count)
        self.assertEqual(1, self.template.request_ids.signer_count)
        signer = self.template.request_ids.signer_id
        self.assertEqual(self.env.user.partner_id, signer.partner_id)
        self.assertTrue(signer.get_info()["items"])
        data = {}
        for key in signer.get_info()["items"]:
            val = signer.get_info()["items"][key].copy()
            val["value"] = "My Name"
            data[key] = val
        res = signer.action_sign(data)
        self.assertEqual(signer.request_id.state, "signed")
        self.assertEqual(res["type"], "ir.actions.act_url")
        self.assertEqual(res["url"], signer.access_url)

    def test_auto_sign_template_cancel(self):
        self.configure_template()
        self.assertEqual(0, self.template.request_count)
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id, default_sign_now=True
            )
        )
        f.save().generate()
        signer = self.template.request_ids.signer_id
        signer.request_id.cancel()
        self.assertEqual(signer.request_id.state, "cancel")

    def test_inalterability(self):
        self.configure_template()
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id, default_sign_now=True
            )
        )
        f.save().generate()
        signer = self.template.request_ids.signer_id
        data = {}
        for key in signer.get_info()["items"]:
            val = signer.get_info()["items"][key].copy()
            val["value"] = "My Name"
            data[key] = val
        signer.action_sign(data)
        self.assertFalse(signer.altered_hash)
        f = Form(
            self.env["sign.oca.template.generate"].with_context(
                default_template_id=self.template.id, default_sign_now=True
            )
        )
        f.save().generate()
        signer_2 = self.template.request_ids.signer_id.filtered(lambda r: r != signer)
        data = {}
        for key in signer_2.get_info()["items"]:
            val = signer_2.get_info()["items"][key].copy()
            val["value"] = "My Name"
            data[key] = val
        signer_2.action_sign(data)
        self.assertFalse(signer_2.altered_hash)
        signer.signature_hash = signer.signature_hash + "AA"
        self.assertTrue(signer.altered_hash)
        signer_2.invalidate_recordset()
        self.assertFalse(signer_2.altered_hash)
        signer.inalterable_hash = signer._get_new_hash(signer.secure_sequence_number)
        signer_2.invalidate_recordset()
        self.assertTrue(signer_2.altered_hash)
