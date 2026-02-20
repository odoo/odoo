import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { CrmTeamSwitcherModelMixin } from "@crm/views/crm_control_panel/crm_team_switcher_model_mixin";

export class CrmActivityModel extends CrmTeamSwitcherModelMixin(ActivityModel) {
    async load(params = {}) {
        const domain = params.domain || this.config.domain;
        params.domain = this._processSearchDomain(params, domain);
        return super.load(params);
    }
}
