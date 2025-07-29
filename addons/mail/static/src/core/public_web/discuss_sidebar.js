import { Component, useSubEnv } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DiscussActions } from "../common/discuss_actions";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = { DiscussActions, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        useSubEnv({ inDiscussSidebar: true });
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
