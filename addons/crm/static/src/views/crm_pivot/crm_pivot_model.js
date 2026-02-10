import { CrmTeamSwitcherModelMixin } from "@crm/views/crm_control_panel/crm_team_switcher_model_mixin";
import { PivotModel } from "@web/views/pivot/pivot_model";

export class CrmPivotModel extends CrmTeamSwitcherModelMixin(PivotModel) {
    async load(searchParams) {
        const domain = searchParams.domain || [];
        searchParams.domain = this._processSearchDomain(searchParams, domain);
        return super.load(searchParams);
    }
}
