import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ProjectTaskModelMixin } from "./project_task_model_mixin";

export class ProjectTaskRelationalModel extends ProjectTaskModelMixin(RelationalModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }
}
