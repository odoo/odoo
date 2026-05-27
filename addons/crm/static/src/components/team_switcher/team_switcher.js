import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

export class TeamSwitcher extends Component {
    static template = "crm.team_switcher";
    static props = {};
    static components = { Dropdown, DropdownItem };

    get allTeamsLabel() {
        return _t("All");
    }

    get currentLabel() {
        return this.teams.find((t) => t.id === this.selectedTeamId)?.name ?? this.allTeamsLabel;
    }

    get isActive() {
        return (
            this.env.searchModel.context.show_team_switcher &&
            this.teams.length
        );
    }

    get selectedTeamId() {
        return this.env.searchModel.state.switcherTeamId;
    }

    get teams() {
        return this.env.searchModel.state.switcherTeams;
    }

    /**
     * Update the team switcher selected team:
     * - the search domain is updated to only display the crm.lead records related to the team
     * - the team related stages are displayed
     * - the team is used as default on crm.lead and crm.stage records creation
     * @param {Number | false} teamId Optional id of the new selected team, fallback on "All" (= false).
     */
    onSelect(teamId=false) {
        if (this.selectedTeamId === teamId) {
            return;
        }
        this.env.searchModel._updateSwitcherSelection(teamId);
    }
};
