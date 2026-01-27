import { DISCUSS_SIDEBAR_COMPACT_LS } from "@mail/core/public_web/discuss_app_model";

import { Component } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }

    enableSidebarCompact() {
        browser.localStorage.setItem(DISCUSS_SIDEBAR_COMPACT_LS, true);
        this.store.discuss._recomputeIsSidebarCompact++;
    }

    disableSidebarCompact() {
        browser.localStorage.removeItem(DISCUSS_SIDEBAR_COMPACT_LS);
        this.store.discuss._recomputeIsSidebarCompact++;
    }
}
