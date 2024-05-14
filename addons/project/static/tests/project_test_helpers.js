import { defineModels } from "@web/../tests/web_test_helpers";
import { BurndownChart } from "@project/../tests/mock_server/mock_models/burndown_chart";
import { ProjectProject } from "@project/../tests/mock_server/mock_models/project_project";
import { ProjectUpdate } from "@project/../tests/mock_server/mock_models/project_update";
import { ProjectTaskType } from "@project/../tests/mock_server/mock_models/project_task_type";
import { ProjectProjectStage } from "@project/../tests/mock_server/mock_models/project_project_stage";
import { ProjectTask } from "@project/../tests/mock_server/mock_models/project_task";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { ProjectMilestone } from "@project/../tests/mock_server/mock_models/project_milestone";

export function defineProjectModels() {
    return defineModels(projectModels);
}

export const projectModels = {
    ...mailModels,
    BurndownChart,
    ProjectTaskType,
    ProjectUpdate,
    ProjectProjectStage,
    ProjectProject,
    ProjectTask,
    ProjectMilestone,
};
