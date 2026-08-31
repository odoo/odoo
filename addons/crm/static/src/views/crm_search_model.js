import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";

import { computed, proxy } from "@odoo/owl";

export class CrmSearchModel extends SearchModel {

    switcherTeam = computed(() => this.state.switcherTeams.find((t) => t.id === this.state.switcherTeamId));

    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.state = proxy({
            switcherAvailable: false, // Whether or not there's enough teams in DB to display the switcher.
            switcherTeams: [], // Teams to display in the switcher.
            switcherTeamId: null, // Selected team id ("undefined" = "All Sales Teams")
        });
    }

    /**
     * Whether or not the switcher is actually displayed.
     */
    get isTeamSwitcherEnabled() {
        return this.showTeamSwitcher && this.state.switcherAvailable;
    }

    /**
     * Whether or not the view would like to display the team switcher.
     */
    get showTeamSwitcher() {
        return !!this._actionContext.show_team_switcher;
    }

    /**
     * @override
     * Init the switcher teams and selection.
     */
    async load(config) {
        // Keep a reference to the original action context so "_updateActionContext" can
        // later patch it to affect the context of the "New" button form view.
        this._actionContext = config.context;
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
            available: this.state.switcherAvailable,
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
            this.state.switcherAvailable = state.teamSwitcherState.available;
            this.state.switcherTeams = state.teamSwitcherState.teams;
            this.state.switcherTeamId = state.teamSwitcherState.teamId;
        }
    }

    /**
     * @override
     * Update the search context so the selected team is used as the default when
     * creating crm.lead records via quick create, business card, ... and creating crm.stage records.
     * Also ensure that only stages related to the selected team are displayed (see _read_group_stage_ids).
     */
    _getContext() {
        const context = super._getContext();
        if (!this.state.switcherTeamId) {
            return context;
        }
        return {
            ...context,
            default_team_id: this.state.switcherTeamId,
            default_team_ids: [this.state.switcherTeamId], // for stages
        };
    }

    /**
     * @override
     * Update search domain depending on the team switcher selection.
     * Showing all "crm.lead" records assigned to the team + the unassigned ones which
     * happens to be part of the team visible stages.
     */
    _getDomain(params = {}) {
        const domain = super._getDomain({ ...params, raw: true }); // Force raw to simplify
        const team = this.switcherTeam();
        if (!team) {
            return params.raw ? domain : domain.toList(this.domainEvalContext);
        }
        const switcherDomain = Domain.and([domain, new Domain(team.switcher_domain)]);
        return params.raw ? switcherDomain : switcherDomain.toList(this.domainEvalContext);
    }

    /**
     * Initialize the team switcher by:
     * - checking whether the view would like the switcher (showTeamSwitcher)
     * - checking whether there are enough teams to actually show it (switcherAvailable)
     * - retrieving the list of crm teams to display (switcherTeams)
     * - restoring the previously selected team (switcherTeamId)
     *
     * The initialization is skipped if the team switcher state is present
     * in the config state as it'll be restored with "_importState".
     */
    async _initSwitcher(config) {
        if (!this.showTeamSwitcher || config.state?.teamSwitcherState) {
            return;
        }
        // Retrieve team switcher data
        const { available, teams } = await this.orm
            .cache({
                type: "disk",
                update: "always",
                callback: (result, hasChanged) => {
                    if (hasChanged) {
                        this.state.switcherAvailable = result.available;
                        this.state.switcherTeams = result.teams;
                        this._initSwitcherSelection(true);
                    }
                },
            })
            .call("crm.team", "get_team_switcher_data");
        this.state.switcherAvailable = available;
        this.state.switcherTeams = teams;
        this._initSwitcherSelection();
    }

    /**
     * Init the switcher selected team by retrieving it from
     * the local storage or fallback on "All Sales Teams".
     */
    _initSwitcherSelection(loaded=false) {
        let teamId = JSON.parse(browser.localStorage.getItem("crm.switcher_team_id"));
        const isValid = this.state.switcherTeams.find((t) => t.id === teamId);
        if (!isValid) {
            // Fallback on "All Sales Teams"
            teamId = undefined;
        }
        if (teamId === this.state.switcherTeamId) {
            // Already current one, nothing to do
            return;
        }
        // Update the selected team
        // If already loaded: notify to recompute the search context and domain.
        this._updateSwitcherSelection(teamId, loaded);
    }

    /**
     * Set the team as "default_team_id" in the action context.
     * Useful to get the team as default when creating "crm.lead" records via the "New" button
     * as the form is opened using the original action context, not the current search context.
     * Also updating the globalContext (= action context one-time copy when the search model is loaded)
     * to prevent stale data.
     */
    _updateActionContext(teamId) {
        for (const context of [this._actionContext, this.globalContext]) {
            if (!context) {
                continue;
            }
            if (teamId) {
                context.default_team_id = teamId;
            } else {
                delete context.default_team_id;
            }
        }
    }

    /**
     * Update the team switcher selected team.
     * @param {Number} teamId Id of the new selected team, "undefined" fallbacks on "All Sales Team".
     * @param {Boolean} notify Whether or not to notify to recompute the search context and domain.
     */
    _updateSwitcherSelection(teamId, notify=true) {
        this.state.switcherTeamId = teamId;
        this._updateActionContext(teamId);
        if (teamId) {
            browser.localStorage.setItem("crm.switcher_team_id", JSON.stringify(teamId));
        } else {
            browser.localStorage.removeItem("crm.switcher_team_id");
        }
        if (notify) {
            this._notify();
        }
    }

    // ===========================================
    // Offline Mode
    // ===========================================

    /**
     * @override
     * In offline mode, restore the current search selected team.
     */
    applySearch(search) {
        // Restore the search (without the team)
        this.blockNotification = true; // Prevent notify
        super.applySearch({ ...search, facets: search.facets.filter((f) => !f.isTeamFacet) });
        this.blockNotification = false;
        // Restore the team
        if (search.teamId !== this.state.switcherTeamId) {
            this._updateSwitcherSelection(search.teamId);
            return;
        }
        this._notify();
    }

    /**
     * @override
     * In offline mode, the team switcher dropdown is disabled to reduce complexity.
     * Instead, showing the current search selected team in the search facets.
     */
    getCurrentSearch() {
        const search = super.getCurrentSearch();
        const team = this.switcherTeam();
        if (!team) {
            return search;
        }
        return {
            ...search,
            facets: [
                ...search.facets,
                { type: "field", icon: "filter_alt", title: _t("Team"), values: [team.name], isTeamFacet: true },
            ],
            teamId: team.id,
        };
    }
};
