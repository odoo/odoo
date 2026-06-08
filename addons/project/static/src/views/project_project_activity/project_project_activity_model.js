import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ProjectModelMixin } from "../project_model_mixin";

export class ProjectActivityModel extends ProjectModelMixin(ActivityModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }
}
