from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSkillTypeDependsCompleteness(TransactionCase):
    def test_display_name_follows_is_certification(self):
        skill_type = self.env["hr.skill.type"].create({"name": "Depends probe"})
        self.assertDependsComplete(
            skill_type,
            computed_fields=["display_name"],
            probe_fields=["name", "is_certification"],
        )

    def test_an_individual_skill_name_follows_its_skill_and_level(self):
        skill_type = self.env["hr.skill.type"].create({"name": "Depends skills"})
        level = self.env["hr.skill.level"].create(
            {
                "name": "Depends level",
                "skill_type_id": skill_type.id,
                "level_progress": 10,
            }
        )
        skill = self.env["hr.skill"].create(
            {"name": "Depends skill", "skill_type_id": skill_type.id}
        )
        employee = self.env["hr.employee"].create({"name": "Depends employee"})
        row = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": skill.id,
                "skill_level_id": level.id,
                "skill_type_id": skill_type.id,
            }
        )
        self.assertEqual(row.display_name, "Depends skill: Depends level")
        skill.name = "Renamed skill"
        level.name = "Renamed level"
        self.assertEqual(row.display_name, "Renamed skill: Renamed level")
