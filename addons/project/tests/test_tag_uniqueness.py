from odoo.tests import tagged

from .test_project_base import TestProjectCommon


@tagged("post_install", "-at_install")
class TestTagNameUniqueness(TestProjectCommon):
    def test_translated_tag_name_is_still_unique(self) -> None:
        self.env["res.lang"]._activate_lang("fr_FR")
        tag = self.env["project.tags"].create({"name": "Uniqueness"})
        tag.with_context(lang="fr_FR").name = "Unicite"
        self.env.flush_all()

        with self.assertRaises(Exception):
            self.env["project.tags"].create({"name": "Uniqueness"})
            self.env.flush_all()


@tagged("post_install", "-at_install")
class TestTagReadsInProjectContext(TestProjectCommon):
    def test_a_project_context_keeps_the_callers_order_and_every_tag(self) -> None:
        Tags = self.env["project.tags"]
        tags = Tags.create([{"name": "Alpha"}, {"name": "Beta"}, {"name": "Gamma"}])
        in_project = Tags.with_context(project_id=self.project_pigs.id)
        domain = [("id", "in", tags.ids)]

        self.assertEqual(
            [
                r["name"]
                for r in in_project.search_read(domain, ["name"], order="name desc")
            ],
            ["Gamma", "Beta", "Alpha"],
        )
        self.assertEqual(
            [r["name"] for r in in_project.search_read(domain, ["name"], offset=1)],
            ["Beta", "Gamma"],
        )
        groups = in_project.formatted_read_group(domain, ["name"], ["__count"])
        self.assertEqual(len(groups), 3)
