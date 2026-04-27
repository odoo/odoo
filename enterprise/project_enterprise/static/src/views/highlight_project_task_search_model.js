import { ProjectTaskSearchModel } from "./project_task_search_model";
import { Domain } from "@web/core/domain";

export class HighlightProjectTaskSearchModel extends ProjectTaskSearchModel {
    _getDomain(params = {}) {
        let domain = super._getDomain(params);
        if (this.highlightPlannedIds?.length) {
            domain = Domain.and([domain, [["id", "in", this.highlightPlannedIds]]]);
            domain = params.raw ? domain : domain.toList();
        }
        return domain;
    }

    async load(config) {
        await super.load(config);
        if (this.context && this.context.highlight_conflicting_task) {
            this.highlightPlannedIds = await this.orm.search("project.task", [
                ["planning_overlap", "!=", false],
            ]);
        }
    }
}
