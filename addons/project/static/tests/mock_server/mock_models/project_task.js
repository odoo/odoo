import { models } from "@web/../tests/web_test_helpers";

export class ProjectTask extends models.ServerModel {
    _name = "project.task";

    plan_task_in_calendar(idOrIds, values) {
        return this.write(idOrIds, values);
    }
}
