import { CrmTeamSwitcherModelMixin } from "@crm/views/crm_control_panel/crm_team_switcher_model_mixin";
import { GraphModel } from "@web/views/graph/graph_model";

export class CrmGraphModel extends CrmTeamSwitcherModelMixin(GraphModel) {
    async load(searchParams) {
        const domain = searchParams.domain || [];
        searchParams.domain = this._processSearchDomain(searchParams, domain);
        return super.load(searchParams);
    }
}
