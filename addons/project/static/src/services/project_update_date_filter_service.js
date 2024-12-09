import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";

class ProjectUpdateDateFilter {
    projectId = null;

    initializeDates(projectId) {
        if (projectId !== this.projectId) {
            this.projectId = projectId;
            this.startDate = this.endDate = false;
        }
    }

    get dates() {
        return pick(this, "startDate", "endDate");
    }

    set dates({ startDate, endDate }) {
        Object.assign(this, { startDate, endDate });
    }
}

export const projectUpdateDateFilterService = {
    dependencies: [],
    async start() {
        return new ProjectUpdateDateFilter();
    },
};

registry.category("services").add("project_update_date_filter", projectUpdateDateFilterService);
