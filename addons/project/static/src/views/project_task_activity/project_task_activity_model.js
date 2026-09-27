import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskActivityModel extends ProjectTaskModelMixin(ActivityModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }
}
