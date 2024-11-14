# Part of Odoo. See LICENSE file for full copyright and licensing details.


import csv

from odoo.modules.module import get_resource_path
from odoo.tests.common import TransactionCase, users
from odoo.tools import file_open


class ResPartnerAddressGet(TransactionCase):
    def setUp(self):
        super().setUp()
        self.demo = self.env.ref("base.user_demo")

    def _create_family(self):
        partners = self.env["res.partner"].sudo()

        main = partners.create(
            {
                "name": "main",
                "parent_id": None,
                "is_company": False,
                "type": "contact",
            }
        )
        partners |= main

        child_level11 = partners.create(
            {
                "name": "child_level11",
                "parent_id": main.id,
                "is_company": False,
                "type": "delivery",
            }
        )
        partners |= child_level11

        child_level12 = partners.create(
            {
                "name": "child_level12",
                "parent_id": main.id,
                "is_company": False,
                "type": "delivery",
            }
        )
        partners |= child_level12

        child_level21 = partners.create(
            {
                "name": "child_level21",
                "parent_id": child_level11.id,
                "is_company": False,
                "type": "invoice",
            }
        )
        partners |= child_level21

        child_level22 = partners.create(
            {
                "name": "child_level22",
                "parent_id": child_level11.id,
                "is_company": False,
                "type": "private",
            }
        )
        partners |= child_level22
        partners = partners.with_user(self.env.uid)
        partners.invalidate_cache()
        partners.clear_caches()
        return self.env["res.partner"].search([("id", "in", partners.ids)])

    def test_res_partner_address_get_many_cases_demo(self):
        """Test delivery and contact combinations case of use for 3 levels based on csv file
        The csv file was used with the old version of odoo in order to get the results in order
        to compare with new results of latest changes to partner.address_get method

        It creates the following family of partners:

        -> main
            -> child_level11
                -> child_level21
                -> child_level22
            -> child_level12
        """
        # Tricky case to force using a sort using char starts with '1' in order to check if it working well
        self.env.cr.execute("ALTER SEQUENCE res_partner_id_seq RESTART WITH 99996")
        partners = self._create_family()
        partner_id_names = {p_test.id: p_test.name for p_test in partners}
        name_partners = {p_test.name: p_test for p_test in partners}

        # The csv file was generated using the following script:
        #   - https://gist.github.com/moylop260/b603e9d2c4ca65a68f09031d380c6219
        csv_path = get_resource_path("base", "tests", "partner_address_type.csv")
        with file_open(csv_path) as fcomb:
            reader = csv.DictReader(fcomb)
            for line, record in enumerate(reader, start=2):
                name_partners["main"].write(
                    {
                        "type": record["main_level"],
                        "is_company": record["main_level_is_company"].lower() == "true",
                    }
                )

                name_partners["child_level11"].write(
                    {
                        "type": record["child_level11"],
                        "is_company": record["child_level11_is_company"].lower() == "true",
                    }
                )
                name_partners["child_level12"].write(
                    {
                        "type": record["child_level12"],
                        "is_company": record["child_level12_is_company"].lower() == "true",
                    }
                )
                name_partners["child_level21"].write(
                    {
                        "type": record["child_level21"],
                        "is_company": record["child_level21_is_company"].lower() == "true",
                    }
                )
                name_partners["child_level22"].write(
                    {
                        "type": record["child_level22"],
                        "is_company": record["child_level22_is_company"].lower() == "true",
                    }
                )

                for current_partner in partners:
                    partner_id_type = current_partner.with_user(self.demo.id).address_get(["delivery"])
                    children = current_partner.search([("id", "child_of", current_partner.id)])
                    children_data = children.read(["name", "is_company", "type", "parent_id"])
                    for address_type in ["contact", "delivery"]:
                        partner_id = partner_id_type.get(address_type)
                        value = partner_id_names.get(partner_id)
                        csv_column_type = f"{address_type}_{current_partner.name}"
                        # print(f"{value},", end="")
                        self.assertEqual(
                            value,
                            record[csv_column_type],
                            f"The partner_type {address_type} returns different results expected {record[csv_column_type]} "
                            f"but {value} found at line {line}. Current structure {children_data}",
                        )

    def test_res_partner_address_archived(self):
        partners = self._create_family()
        name_partners = {p_test.name: p_test for p_test in partners}
        partner_id_names = {p_test.id: p_test.name for p_test in partners}
        current_partner = name_partners["main"]
        partner_type_id = current_partner.with_user(self.demo.id).address_get(["delivery"])
        partner_type_name = {
            partner_type: partner_id_names[partner_id] for partner_type, partner_id in partner_type_id.items()
        }
        expected = {"contact": "main", "delivery": "child_level11"}
        self.assertEqual(expected, partner_type_name)
        current_partner.invalidate_cache(["child_ids"])

        # Archived
        name_partners["child_level11"].write({"active": False})
        partner_type_id_archived = current_partner.with_user(self.demo.id).address_get(["delivery"])
        partner_type_name_archived = {
            partner_type: partner_id_names[partner_id] for partner_type, partner_id in partner_type_id_archived.items()
        }
        expected_archived = {"contact": "main", "delivery": "child_level12"}
        self.assertEqual(expected_archived, partner_type_name_archived)
        current_partner.invalidate_cache(["child_ids"])
        name_partners["child_level11"].write({"active": True})

    @users("__system__")
    def test_res_partner_address_private_system(self):
        partners = self._create_family()
        name_partners = {p_test.name: p_test for p_test in partners}
        partner_id_names = {p_test.id: p_test.name for p_test in partners}
        current_partner = name_partners["main"]

        # private
        name_partners["child_level11"].write({"type": "private"})
        partners.invalidate_cache()

        # admin bypassing ir rule
        partner_type_id_admin_private = current_partner.sudo().address_get(["private"])
        partner_type_name_admin_private = {
            partner_type: partner_id_names[partner_id]
            for partner_type, partner_id in partner_type_id_admin_private.items()
        }
        expected_admin_private = {"contact": "main", "private": "child_level11"}
        self.assertEqual(expected_admin_private, partner_type_name_admin_private)

    @users("demo")
    def test_res_partner_address_private_demo(self):
        partners = self._create_family()
        name_partners = {p_test.name: p_test for p_test in partners}
        partner_id_names = {p_test.id: p_test.name for p_test in partners}
        current_partner = name_partners["main"]
        # private
        name_partners["child_level11"].sudo().write({"type": "private"})
        partners.invalidate_cache()

        partner_type_id_demo_private = current_partner.address_get(["private"])
        partner_type_name_demo_private = {
            partner_type: partner_id_names[partner_id]
            for partner_type, partner_id in partner_type_id_demo_private.items()
        }
        expected_demo_private = {"contact": "main", "private": "main"}
        self.assertEqual(expected_demo_private, partner_type_name_demo_private)

    def test_res_partner_address_browse_null(self):
        result = self.env["res.partner"].address_get(["contact", "delivery"])
        self.assertEqual(result, {"delivery": False, "contact": False}, "BrowseNull returned different values")
