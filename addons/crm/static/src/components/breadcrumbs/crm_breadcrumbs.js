import { Breadcrumbs } from "@web/search/breadcrumbs/breadcrumbs";
import { TeamSwitcher } from "@crm/components/team_switcher/team_switcher";

export class CrmBreadcrumbs extends Breadcrumbs {
    static template = "crm.Breadcrumbs";
    static components = {
        ...Breadcrumbs.components,
        TeamSwitcher,
    };

    get hasTeamSwitcher() {
        return this.env.searchModel.isTeamSwitcherEnabled;
    }
}
