import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ProjectModelMixin } from "./project_model_mixin";

export class ProjectRelationalModel extends ProjectModelMixin(RelationalModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }
}
