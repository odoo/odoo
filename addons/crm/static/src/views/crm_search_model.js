import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { SearchModel } from "@web/search/search_model";

/**
 * Give the possibility to add a team switcher.
 * Renaming the "team_id" field search filter into "crm_team_switcher" will change it into a team switcher where:
 * - Only one team can be selected at a time ("All" option available)
 * - The selected team is saved in local storage to be restored as default filter (fallback on first team if no selection).
 * - The context is updated to set selected team as default on crm.lead record creation and display the related stages.
 */
export class CrmSearchModel extends SearchModel {
    /**
     * @override
     * Load filter team options to restore selected team or fallback on first.
     */
    async load(config) {
        await super.load(config);
        if (!this.tsSearchItem) {
            return;
        }
        await this.loadLazyParentFilter(this.tsSearchItem.id);
        const savedOptionId = browser.localStorage.getItem("selectedTeamOptionId");
        if (savedOptionId === this.tsAllOptionId) {
            return;
        }
        const optionId = this.tsSearchItem.options.find((o) => o.id === savedOptionId)
            ? savedOptionId
            : this.tsSearchItem.options[0]?.id;
        if (optionId && this.tsSelectedOptionId !== optionId) {
            this.toggleTeamSwitcherFilter(optionId);
        }
    }

    get tsAllOptionId() {
        return "all";
    }

    /**
     * Name of the "team_id" search filter used to activate the team switcher.
     */
    get tsFilterName() {
        return "crm_team_switcher";
    }

    get tsSearchItem() {
        return this.getSearchItems(
            (i) => i.name === this.tsFilterName && i.optionsParams.fieldName === "team_id"
        )?.[0];
    }

    /**
     * Get the team switcher selected option id directly from the query object.
     */
    get tsSelectedOptionId() {
        if (!this.tsSearchItem) {
            return null;
        }
        const queryItem = this.query.find((queryElem) => queryElem.searchItemId === this.tsSearchItem.id);
        return queryItem?.generatorId || null;
    }

    /**
     * @override
     * Remove team switcher facet.
     * Selected team filter only editable from the switcher dropdown.
     */
    _getFacets() {
        const facets = super._getFacets();
        const tsGroupId = this._getGroups().find((g) =>
            g.activeItems[0].searchItemId === this.tsSearchItem?.id
        )?.id;
        if (!tsGroupId) {
            return facets;
        }
        const index = facets.findIndex((f) => f.groupId === tsGroupId);
        if (index !== -1) {
            facets.splice(index, 1);
        }
        return facets;
    }

    /**
     * @override
     * Set selected team as default team on crm.lead record creation.
     * Notify that a team has been selected so stages can be updated accordingly (cf _read_group_stage_ids).
     */
    _getSearchItemContext(activeItem) {
        const context = super._getSearchItemContext(activeItem);
        if (activeItem.searchItemId !== this.tsSearchItem?.id) {
            return context;
        }
        const tsSelectedOption = this.tsSearchItem.optionsParams.customOptions.find(
            (o) => o.id === this.tsSelectedOptionId
        );
        if (!tsSelectedOption) {
            return context;
        }
        return {
            ...(context ?? {}),
            default_team_id: new Domain(tsSelectedOption.domain).toList()[0][2], // TODO do not work for list view ?
            has_team_selection: true,
        };
    }

    /**
     * @override
     */
    toggleParentFilter(searchItemId, generatorId) {
        if (searchItemId !== this.tsSearchItem?.id) {
            super.toggleParentFilter(searchItemId, generatorId);
            return;
        }
        this.toggleTeamSwitcherFilter(generatorId);
    }

    /**
     * Toggle team option in the team switcher.
     * - Only one team can be selected at a time.
     * - Selecting a different team automatically unselects the previous active team.
     */
    toggleTeamSwitcherFilter(optionId) {
        // Unselect current: fallback on "All"
        if (optionId === this.tsSelectedOptionId) {
            super.toggleParentFilter(this.tsSearchItem.id, optionId);
            browser.localStorage.setItem("selectedTeamOptionId", this.tsAllOptionId);
            return;
        }
        // Unselect previous active option
        const index = this.query.findIndex(
            (queryElem) =>
                queryElem.searchItemId === this.tsSearchItem.id &&
                "generatorId" in queryElem &&
                queryElem.generatorId === this.tsSelectedOptionId
        );
        if (index !== -1) {
            this.query.splice(index, 1);
        }
        // Select new option
        super.toggleParentFilter(this.tsSearchItem.id, optionId);
        browser.localStorage.setItem("selectedTeamOptionId", optionId);
    }
}
