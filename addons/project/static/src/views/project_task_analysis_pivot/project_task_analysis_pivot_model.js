import { PivotModel } from "@web/views/pivot/pivot_model";
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskAnalysisPivotModel extends ProjectTaskModelMixin(PivotModel) {
    async load(searchParams) {
        const domain = searchParams.domain || [];
        searchParams.domain = this._processSearchDomain(domain);
        const result = await super.load(searchParams);
        if (searchParams.context?.hide_count_measure) {
            delete this.metaData.measures.__count;
        }
        return result;
    }
}
