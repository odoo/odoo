import { CrmTeamSwitcherModelMixin } from "@crm/views/crm_control_panel/crm_team_switcher_model_mixin";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class CrmListModel extends CrmTeamSwitcherModelMixin(RelationalModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(params, domain);
        return super.load(params);
    }
}
