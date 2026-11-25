import { Component, usePlugin } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useEnv } from "@web/owl2/utils";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Search Matching Applicants' menu
 *
 * This component is used to search matching skills among the all applicants
 * It's only available in the kanban and list view of the applicants.
 * @extends Component
 */
export class SearchJobApplicant extends Component {
    static template = "hr_recruitment.SearchJobApplicant";
    static components = { DropdownItem };

    action = usePlugin(ActionPlugin);

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    openMatchingJobApplicants() {
        const { globalContext } = this.env.searchModel;
        return this.action.doActionButton({
            type: "object",
            resModel: "hr.job",
            name: "action_job_add_applicants",
            resId: globalContext.active_id,
            context: user.context, // orm.call used to add the user context (lang/tz) automatically
        });
    }
}

export const searchJobApplicant = {
    Component: SearchJobApplicant,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed() {
        const env = useEnv();
        return (
            env.searchModel.resModel === "hr.applicant" &&
            env.searchModel.globalContext.allow_search_matching_applicants &&
            env.config.viewArch.classList.contains('o_search_matching_applicant')
        );
    },
};

cogMenuRegistry.add("search-job-applicants-menu", searchJobApplicant, { sequence: 11 });
