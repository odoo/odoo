import { ControlPanel } from "@web/search/control_panel/control_panel";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

import { onWillStart } from "@odoo/owl";

export class CrmControlPanel extends ControlPanel {
    static template = "crm.ControlPanel";

    setup() {
        super.setup();
        this.selectedCrmTeamsKey = "selectedCrmTeamIds";
        this.state.selectedCrmTeamIds = JSON.parse(browser.localStorage.getItem(this.selectedCrmTeamsKey) || "[]");

        onWillStart(async () => {
            this.accessibleTeams = await this.orm.searchRead("crm.team", [], ["id", "name"]);
            const [userTeams] = await this.orm.read("res.users", [user.userId], ["sale_team_id"]);
            this.state.userMainTeamId = userTeams?.sale_team_id?.[0] || false;
        });
    }

    get teamSwitcherTitle() {
        return _t("Teams");
    }

    getMainTeamLabel(team) {
        if (this.isTeamMain(team.id)) {
            return _t("%s is your Main Team", team.name);
        }
        return _t("Set %s as Main Team", team.name);
    }

    isTeamMain(teamId) {
        if (!this.state.userMainTeamId) {
            return false;
        }
        return this.state.userMainTeamId === teamId;
    }

    isTeamSelected(teamId) {
        return this.state.selectedCrmTeamIds.includes(teamId);
    }

    onSelectCrmTeam(teamId) {
        if (this.isTeamSelected(teamId)) {
            this.state.selectedCrmTeamIds = this.state.selectedCrmTeamIds.filter((id) => id !== teamId);
        } else {
            this.state.selectedCrmTeamIds.push(teamId);
        }
        browser.localStorage.setItem(this.selectedCrmTeamsKey, JSON.stringify(this.state.selectedCrmTeamIds));
        this.env.searchModel.search();
    }

    async onSetMain(teamId) {
        if (!teamId || this.isTeamMain(teamId)) {
            return;
        }
        await this.orm.write("res.users", [user.userId], {
            "sale_team_id": teamId,
        });
        this.state.userMainTeamId = teamId;
    }
}
