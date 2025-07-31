import { useHover } from "@mail/utils/common/hooks";
import { Component, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

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
        this.command = useService("command");
        useSubEnv({ inDiscussSidebar: true });
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
        useSubEnv({
            filteredThreads: (threads) => this.filteredThreads(threads),
        });
    }

    filteredThreads(threads) {
        return threads.filter((thread) => thread.displayInSidebar);
    }

    onClickFindOrStartConversation() {
        this.command.openMainPalette({ searchValue: "@" });
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }

    get optionActions() {
        return [
            {
                id: "toggle-size",
                name: this.store.discuss.isSidebarCompact
                    ? _t("Expand panel")
                    : _t("Collapse panel"),
                icon: this.store.discuss.isSidebarCompact ? "fa fa-expand" : "fa fa-compress",
                onSelected: () =>
                    (this.store.discuss.isSidebarCompact = !this.store.discuss.isSidebarCompact),
            },
        ];
    }
}
