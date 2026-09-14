/** @odoo-module native */
import { Component, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * @extends Component
 */
export class SearchJobApplicant extends Component {
    static template = "hr_recruitment_skills.SearchJobApplicant";
    static components = { CogMenuItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    async openMatchingJobApplicants() {
        const { globalContext } = this.env.searchModel;
        const action = await this.env.services.orm.call(
            "hr.job",
            "action_search_matching_applicants",
            [globalContext.active_id],
        );
        action.help = markup(action.help);
        return this.action.doAction(action);
    }
}

export const searchJobApplicant = {
    Component: SearchJobApplicant,
    groupNumber: COG_GROUP.APP,
    isDisplayed: ({ config, searchModel }) => {
        return (
            searchModel.resModel === "hr.applicant" &&
            searchModel.globalContext.allow_search_matching_applicants &&
            config.viewArch.classList.contains("o_search_matching_applicant")
        );
    },
};

cogMenuRegistry.add("search-job-applicants-menu", searchJobApplicant, { sequence: 11 });
