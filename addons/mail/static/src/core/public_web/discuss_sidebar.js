import { useHover } from "@mail/utils/common/hooks";
import { Component, onMounted, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { ActionList } from "../common/action_list";

import { registry } from "@web/core/registry";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = { ActionList, Dropdown, ResizablePanel };

    setup() {
        super.setup();
        this.command = useService("command");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useSubEnv({ inDiscussSidebar: true });
        onMounted(() => {
            this.mounted = true;
        });
        this.searchHover = useHover(["search-btn", "search-floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = false;
                }
            },
        });
        this.searchFloating = useDropdownState();
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }

    onClickFindOrStartConversation() {
        this.command.openMainPalette({ searchValue: "@" });
    }

    onResize(width) {
        if (!this.mounted) {
            return; // ignore resize from mount not triggered by user
        }
        this.store.discuss.isSidebarCompact = width <= 100;
    }
}
