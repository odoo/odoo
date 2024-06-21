import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class MultiTimeOffGenerationMenu extends Component {
    static template = "hr_holidays.MultipleTimeOffGeneraion";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async openMatchingJobApplicants() {
        const resModel = this.env.searchModel.resModel;
        if (resModel === "hr.leave") {
            return this.action.doAction("hr_holidays.action_hr_leave_generate_multi_wizard");
        } else {
            return this.action.doAction("hr_holidays.action_hr_leave_allocation_generate_multi_wizard");
        }
    }
}

export const multiTimeOffGenerationMenu = {
    Component: MultiTimeOffGenerationMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async ({ config, searchModel }) => {
        return (
            ["hr.leave", "hr.leave.allocation"].includes(searchModel.resModel) &&
            (await user.hasGroup("hr_holidays.group_hr_holidays_user"))
        );
    },
};

cogMenuRegistry.add("multi-time-off-generation-menu", multiTimeOffGenerationMenu, { sequence: 11 });
