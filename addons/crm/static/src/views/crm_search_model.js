import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { SearchModel } from "@web/search/search_model";
import { proxy } from "@odoo/owl";

export class CrmSearchModel extends SearchModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.state = proxy({
            switcherTeams: [],
            switcherTeamId: undefined,
        });
    }

    /**
     * @override
     */
    async load(config) {
        await this._initSwitcher(config);
        await super.load(config);
    }

    /**
     * @override
     * Export team switcher state with the config state.
     */
    exportState() {
        const state = super.exportState();
        state.teamSwitcherState = {
            teams: this.state.switcherTeams,
            teamId: this.state.switcherTeamId,
        };
        return state;
    }

    /**
     * @override
     * Restore team switcher state when the config state is imported (i.e. on switch view).
     */
    _importState(state) {
        super._importState(...arguments);
        if (state.teamSwitcherState) {
            this.state.switcherTeams = state.teamSwitcherState.teams;
            this.state.switcherTeamId = state.teamSwitcherState.teamId;
        }
    }

    /**
     * Initialize the team switcher by:
     * - retrieving the list of crm teams to display
     * - restoring the previously selected team to be applied in the search.
     * The initialization is skipped if the team switcher state is present
     * in the config state as it'll be restored with "_importState".
     */
    async _initSwitcher(config) {
        if (!config.context.show_team_switcher || config.state?.teamSwitcherState) {
            return;
        }
        // Retrieve teams to display in team switcher
        this.state.switcherTeams = await this.orm
            .cache({
                type: "disk",
                update: "always", // Team changes are directly reflected
                callback: (result, hasChanged) => {
                    if (hasChanged) {
                        this.state.switcherTeams = result;
                    }
                },
            })
            .call("crm.team", "get_team_switcher_teams");
        // Restore selected team ("All" = false)
        // If nothing selected or team not accessible anymore, fallback on first team or "All"
        const savedTeamId = JSON.parse(browser.localStorage.getItem("crm.switcher_team_id"));
        const isValid = savedTeamId === false || this.state.switcherTeams.some((t) => t.id === savedTeamId);
        this.state.switcherTeamId = isValid ? savedTeamId : this.state.switcherTeams[0]?.id ?? false;
    }

    /**
     * Update the team switcher selected team.
     * @param {Number | false} teamId Id of the new selected team ("All" = false).
     */
    _updateSwitcherSelection(teamId) {
        this.state.switcherTeamId = teamId;
        browser.localStorage.setItem("crm.switcher_team_id", JSON.stringify(teamId));
        // Update the action context so the selected team is used as the default when
        // creating crm.lead records via the form view.
        // The form is opened using the action context, not the search context.
        const currentActionContext = this.env.services.action.currentController.action.context;
        if (teamId) {
            Object.assign(currentActionContext, { default_team_id: teamId });
        } else {
            delete currentActionContext.default_team_id;
        }
        this._notify();
    }

    /**
     * @override
     * Update the search context so the selected team is used as the default when
     * creating crm.lead records (via quick create, business card, ...) and creating crm.stage records.
     * Also ensure that only stages related to the selected team are displayed (see _read_group_stage_ids).
     */
    _getContext() {
        const context = super._getContext();
        if (this.state.switcherTeamId === undefined) {
            return context;
        }
        let switcherContext = {};
        if (this.state.switcherTeamId) {
            // Specific team
            switcherContext = {
                default_team_id: this.state.switcherTeamId,
                default_team_ids: [this.state.switcherTeamId], // for stages
            };
        } else {
            // All teams
            switcherContext = {
                switcher_all_team_ids: this.state.switcherTeams.map((t) => t.id), // for stages
            };
        }
        return {
            ...context,
            ...switcherContext,
        };
    }

    /**
     * @override
     * Update search domain depending on the team switcher selection.
     */
    _getDomain(params = {}) {
        const domain = super._getDomain({ ...params, raw: true }); // Force raw to simplify
        if (this.state.switcherTeamId === undefined) {
            return params.raw ? domain : domain.toList(this.domainEvalContext);
        }
        const teamIds = this.state.switcherTeamId
            ? [this.state.switcherTeamId] // Specific team
            : this.state.switcherTeams.map((t) => t.id); // All teams
        const switcherDomain = Domain.and([domain, new Domain([["team_id", "in", teamIds]])]);
        return params.raw ? switcherDomain : switcherDomain.toList(this.domainEvalContext);
    }
};
