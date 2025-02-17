import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { UserStatusPanel } from "./user_status_panel";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = { Dropdown, DropdownItem, UserStatusPanel };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }
}
