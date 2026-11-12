import { registry } from "@web/core/registry";
import { Component } from '@odoo/owl';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from '@web/core/utils/hooks';
import { openHubItem, savePinnedItemIds } from "./hub_utils";
import { useEnv } from "@web/owl2/utils";

export class HubMenu extends Component {
    static template = "web.HubMenu"; // a submenu with one DropdownItem per hub item
    static components = { Dropdown, DropdownItem };

    actionPlugin = useService("action");
    orm = useService("orm");

    get items() {
        return this.env.config.hub.items;
    }

    openItem(item) {
        const { resModel, resId } = this.env.config.hub;
        openHubItem(this.actionPlugin, item, { resModel, resId }, {
            stackPosition: "replaceCurrentAction",
        })
    }

    isPinned(item) {
        return this.env.config.hub.pinnedItemIds().includes(item.id);
    }

    async checkboxClicked(e, item) {
        e.target.classList.add("o_animate");
        const hub = this.env.config.hub;
        const pinnedItemIds = hub.pinnedItemIds().filter((id) => id !== item.id);
        if (e.target.checked) {
            pinnedItemIds.push(item.id);
        }
        await savePinnedItemIds(this.orm, hub, pinnedItemIds);
    }
}

registry.category("cogMenu").add("hub-menu", {
    Component: HubMenu,
    groupNumber: 1, // lower groupNumber = higher in the menu
    isDisplayed() {
        return !!useEnv().config.hub;
    },
}, { sequence: 1 });
