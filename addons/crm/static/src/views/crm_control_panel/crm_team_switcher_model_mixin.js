import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";

export const CrmTeamSwitcherModelMixin = (T) => class CrmTeamSwitcherModelMixin extends T {
    _processSearchDomain(params, domain) {
        const selectedCrmTeams = JSON.parse(browser.localStorage.getItem("selectedCrmTeamIds") || "[]");
        if (selectedCrmTeams.length) {
            // Check if necessary for other view than kanban.
            // If only kanban, move to kanban model.
            params.context.team_switcher_selected_teams = selectedCrmTeams;
            domain = Domain.and([
                domain,
                [['team_id', 'in', selectedCrmTeams]],
            ]).toList({});
        }
        return domain;
    }
};
