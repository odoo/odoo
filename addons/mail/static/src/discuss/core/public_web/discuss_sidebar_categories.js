import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_sidebar_channel";
import { cleanTerm } from "@mail/utils/common/format";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCategories extends Component {
    static template = "mail.DiscussSidebarCategories";
    static props = {};
    static components = { DiscussSidebarChannel };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.discusscorePublicWebService = useState(useService("discuss.core.public.web"));
        this.state = useState({
            quickSearchVal: "",
        });
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }

    filteredThreads(category) {
        return category.threads.filter((thread) => {
            return (
                (thread.displayToSelf || thread.isLocallyPinned) &&
                (!this.state.quickSearchVal ||
                    cleanTerm(thread.displayName).includes(cleanTerm(this.state.quickSearchVal)))
            );
        });
    }

    get hasQuickSearch() {
        return (
            Object.values(this.store.Thread.records).filter(
                (thread) => thread.is_pinned && thread.model === "discuss.channel"
            ).length > 19
        );
    }

    /** @param {import("models").DiscussAppCategory} category */
    toggleCategory(category) {
        if (this.store.channels.status === "fetching") {
            return;
        }
        category.open = !category.open;
        this.discusscorePublicWebService.broadcastCategoryState(category);
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
