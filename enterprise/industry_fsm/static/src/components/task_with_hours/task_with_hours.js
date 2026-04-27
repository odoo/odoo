import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import {
    TaskWithHours,
    taskWithHours,
} from "@hr_timesheet/components/task_with_hours/task_with_hours";

patch(TaskWithHours.prototype, {
    setup() {
        this.createEditProjectIdsService = useService("create_edit_project_ids");
        super.setup();
    },

    canCreate() {
        const projectIds = this.createEditProjectIdsService.projectIds;
        if (projectIds !== undefined) {
            return (
                Boolean(this.context.default_project_id) &&
                !projectIds.includes(this.props.record.data.project_id[0])
            );
        }
        return super.canCreate();
    },
});

export class FsmTaskWithHours extends TaskWithHours {
    async onWillStart() {
        super.onWillStart();
        await this.createEditProjectIdsService.fetchProjectIds();
    }
}

export const fsmTaskWithHours = {
    ...taskWithHours,
    component: FsmTaskWithHours,
};

registry.category("fields").add("task_with_hours", fsmTaskWithHours, { force: true });
registry.category("fields").add("list.task_with_hours", taskWithHours);
