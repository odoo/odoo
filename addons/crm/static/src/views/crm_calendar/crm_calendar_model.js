import { CalendarModel } from "@web/views/calendar/calendar_model";
import { CrmTeamSwitcherModelMixin } from "@crm/views/crm_control_panel/crm_team_switcher_model_mixin";
import { _t } from "@web/core/l10n/translation";

export class CrmCalendarModel extends CrmTeamSwitcherModelMixin(CalendarModel) {
    async load(params = {}) {
        const domain = params.domain || this.meta.domain;
        params.domain = this._processSearchDomain(params, domain);
        return super.load(params);
    }
}
