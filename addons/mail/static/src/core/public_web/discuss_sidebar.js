import { useHover } from "@mail/utils/common/hooks";
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
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
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.compactHover = useHover(["compact-btn", "compact-floating*"], {
            onHover: () => (this.compactFloating.isOpen = true),
            onAway: () => (this.compactFloating.isOpen = false),
        });
        this.compactFloating = useDropdownState();
    }

    get compactBtnText() {
        if (this.store.discuss.isSidebarCompact) {
            return _t("Expand");
        }
        return _t("Collapse");
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }
}
