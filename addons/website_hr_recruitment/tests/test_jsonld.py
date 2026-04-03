# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteHrRecruitmentJsonLd(TransactionCase):
    def test_job_to_structured_data(self):
        website = self.env.ref("website.default_website")
        address = self.env["res.partner"].create({
            "name": "Job Address",
            "country_id": self.env.ref("base.us").id,
            "city": "New York",
        })
        job = self.env["hr.job"].create({
            "name": "JSON-LD Developer",
            "website_id": website.id,
            "website_published": True,
            "address_id": address.id,
            "website_description": "Developer role for JSON-LD coverage tests.",
        })

        json_ld = job._to_structured_data()
        markup_data = json_ld._render()

        self.assertEqual(markup_data["@type"], "JobPosting")
        self.assertEqual(markup_data["title"], job.name)
        self.assertTrue(markup_data["directApply"])

    def test_job_to_structured_data_summary(self):
        website = self.env.ref("website.default_website")
        job = self.env["hr.job"].create({
            "name": "JSON-LD Analyst",
            "website_id": website.id,
            "website_published": True,
        })

        json_ld_list = job._to_structured_data_summary(website)

        self.assertEqual(len(json_ld_list), 1)
        self.assertEqual(json_ld_list[0]._render()["@type"], "JobPosting")

    def test_jobs_summary_covers_multiple_listing_items(self):
        website = self.env.ref("website.default_website")
        jobs = self.env["hr.job"].create([
            {
                "name": "JSON-LD Job A",
                "website_id": website.id,
                "website_published": True,
            },
            {
                "name": "JSON-LD Job B",
                "website_id": website.id,
                "website_published": True,
            },
        ])

        json_ld_list = jobs._to_structured_data_summary(website)
        markup_types = [schema._render()["@type"] for schema in json_ld_list]

        self.assertEqual(len(json_ld_list), 2)
        self.assertEqual(markup_types, ["JobPosting", "JobPosting"])

    def test_remote_job_uses_telecommute_location_type(self):
        website = self.env.ref("website.default_website")
        job = self.env["hr.job"].create({
            "name": "Remote JSON-LD Job",
            "website_id": website.id,
            "website_published": True,
            "address_id": False,
        })

        markup_data = job._to_structured_data()._render()

        self.assertEqual(markup_data["jobLocationType"], "TELECOMMUTE")
