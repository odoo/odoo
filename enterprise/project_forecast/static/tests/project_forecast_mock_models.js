import { planningModels } from "@planning/../tests/planning_mock_models";
import { projectModels } from "@project/../tests/project_models";
import { fields } from "@web/../tests/web_test_helpers";

export class PlanningSlot extends planningModels.PlanningSlot {
    _name = "planning.slot";

    project_id = fields.Many2one({ relation: "project.project" });
}

export class ProjectProject extends projectModels.ProjectProject {}

planningModels.PlanningSlot = PlanningSlot;
planningModels.ProjectProject = ProjectProject;
