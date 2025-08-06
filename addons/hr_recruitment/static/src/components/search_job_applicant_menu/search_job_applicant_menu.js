import { Component, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Search Matching Applicants' menu
 *
 * This component is used to search matching skills among the all applicants
 * It's only available in the kanban and list view of the applicants.
 * @extends Component
 */
export class SearchJobApplicant extends Component {
    static template = "hr_recruitment_skills.SearchJobApplicant";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async openMatchingJobApplicants() {
        const { globalContext } = this.env.searchModel;
        const action = await this.env.services.orm.call(
            "hr.job",
            "action_search_matching_applicants",
            [globalContext.active_id]
        );
        action.help = markup(action.help);
        return this.action.doAction(action);
    }
}

export const searchJobApplicant = {
    Component: SearchJobApplicant,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, searchModel }) => {
        return (
            searchModel.resModel === "hr.applicant" &&
            searchModel.globalContext.allow_search_matching_applicants &&
            config.viewArch.classList.contains('o_search_matching_applicant')
        );
    },
};

cogMenuRegistry.add("search-job-applicants-menu", searchJobApplicant, { sequence: 11 });
