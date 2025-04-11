import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class LoadFromWebsite extends Component {
    static template = "hr_holidays.LoadFromWebsite";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.notificationService = useService("notification");
    }

    async createPublicHolidayFromWebsite() {
        const response = await rpc("/web/dataset/call_kw", {
            model: "resource.calendar.leaves",
            method: "load_public_holidays",
            args: [this.env.searchModel.context.allowed_company_ids],
            kwargs: {},
        });
        await this.env.model.load();
        response.forEach((item) => {
            this.notificationService.add(item.message, {
                title: item.title,
                type: item.type,
            });
        });
    }
}

export const loadFromWebsite = {
    Component: LoadFromWebsite,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, searchModel }) =>
        searchModel.resModel === "resource.calendar.leaves" &&
        config.viewArch.classList.contains("o_load_from_website"),
};

cogMenuRegistry.add("load-from-website-menu", loadFromWebsite, { sequence: 11 });
