import { GraphModel } from "@web/views/graph/graph_model";
import { ProjectTaskModelMixin } from "../project_task_model_mixin";

export class ProjectTaskAnalysisGraphModel extends ProjectTaskModelMixin(GraphModel) {
    async load(searchParams) {
        const domain = searchParams.domain || [];
        searchParams.domain = this._processSearchDomain(domain);
        return super.load(searchParams);
    }

    _buildMetaData(params) {
        const metaData = super._buildMetaData(params);
        if (this.searchParams.context?.hide_count_measure) {
            delete metaData.measures.__count;
        }
        return metaData;
    }
}
