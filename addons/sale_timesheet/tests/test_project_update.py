from odoo.tests import tagged

from odoo.addons.project.tests.test_project_update_flow import TestProjectUpdate


@tagged("-at_install", "post_install")
class TestProjectUpdateSaleTimesheet(TestProjectUpdate):
    def test_project_update_description_profitability(self):
        self.project_pigs.allow_billable = True
        template_values = self.env["project.update"]._prepare_update_rendering_context(
            self.project_pigs
        )

        self.assertEqual(
            template_values["profitability"]["total"]["costs"],
            0.0,
            "Project costs used in the template should be well defined",
        )
        self.assertEqual(
            template_values["profitability"]["total"]["revenues"],
            0.0,
            "Project revenues used in the template should be well defined",
        )
        self.assertEqual(
            template_values["profitability"]["total"]["margin"],
            0,
            "Margin used in the template should be well defined",
        )
        self.assertEqual(
            template_values["profitability"]["total"]["margin_percentage"],
            "0",
            "Margin percentage used in the template should be well defined",
        )

    def test_project_update_panel_profitability_no_billable(self):
        try:
            self.project_pigs.action_view_timesheet()
        except Exception as e:
            raise AssertionError(
                "Error raised unexpectedly while calling the action defined in profitalities action panel data ! Exception : "
                + e.args[0]
            ) from e
