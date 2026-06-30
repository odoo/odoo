import { PivotModel } from "@web/views/pivot/pivot_model";
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskPivotModel extends ProjectTaskModelMixin(PivotModel) {
    async load(searchParams) {
        const domain = searchParams.domain || [];
        searchParams.domain = this._processSearchDomain(domain);
        return super.load(searchParams);
    }
}
