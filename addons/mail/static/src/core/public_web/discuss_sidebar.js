import { ActionList } from "../common/action_list";
import { DiscussSearch } from "./discuss_search";
import { DISCUSS_SIDEBAR_COMPACT_LS } from "@mail/core/public_web/discuss_app_model";

import { Component, onMounted, useSubEnv } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useService } from "@web/core/utils/hooks";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = { ActionList, DiscussSearch, ResizablePanel };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useSubEnv({ inDiscussSidebar: true });
        onMounted(() => {
            this.mounted = true;
        });
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }

    onResize(width) {
        if (!this.mounted) {
            return; // ignore resize from mount not triggered by user
        }
        if (width <= 100) {
            browser.localStorage.setItem(DISCUSS_SIDEBAR_COMPACT_LS, true);
        } else {
            browser.localStorage.removeItem(DISCUSS_SIDEBAR_COMPACT_LS);
        }
        this.store.discuss._recomputeIsSidebarCompact++;
    }
}
