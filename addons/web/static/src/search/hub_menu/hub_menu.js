import { registry } from "@web/core/registry";
import { Component } from '@odoo/owl';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpcBus } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { openHubItem } from "./hub_utils";
import { useEnv } from "@web/owl2/utils";

export class HubMenu extends Component {
    static template = "web.HubMenu"; // a submenu with one DropdownItem per hub item
    static components = { Dropdown, DropdownItem };

    actionPlugin = useService("action");
    orm = useService("orm");

    get items() {
        return this.env.config.hub.action.item_ids;
    }

    openItem(item) {
        const { resId, action: hubAction } = this.env.config.hub;
        openHubItem(this.actionPlugin, item, {resModel: hubAction.res_model, resId}, {
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
        hub.pinnedItemIds.set(pinnedItemIds);
        await this.orm.call("res.users.settings", "set_hub_setting", [
            user.settings.id,
            hub.action.id,
            hub.resId,
            pinnedItemIds,
        ]);
        // loaded actions carry the pinned items of their hub
        rpcBus.trigger("CLEAR-CACHES", "/web/action/load");
    }
}

registry.category("cogMenu").add("hub-menu", {
    Component: HubMenu,
    groupNumber: 1, // lower groupNumber = higher in the menu
    isDisplayed() {
        return !!useEnv().config.hub;
    },
}, { sequence: 1 });
