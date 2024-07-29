import { useVisible } from "@mail/utils/common/hooks";
import { Component, useRef, useState, useSubEnv } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

const ACTIVE_VISIBILITY = {
    VISIBLE: "VISIBLE",
    HIDDEN_TOP: "HIDDEN_TOP",
    HIDDEN_BOTTOM: "HIDDEN_BOTTOM",
};

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = {};

    /** @type {ReturnType<import("@odoo/owl").useRef>} */
    activeRef;

    setup() {
        super.setup();
        this.ACTIVE_VISIBILITY = ACTIVE_VISIBILITY;
        this.root = useRef("root");
        this.state = useState({ activeVisibility: null });
        this.activeVisible = useVisible(this.activeRef, () => this.updateActiveVisible(), {
            log: true,
        });
        this.store = useState(useService("mail.store"));
        window.aku = this;
        useSubEnv({
            discussSidebar: {
                setActiveRef: (ref) => {
                    this.activeRef = ref;
                    this.activeVisible.setNewRef(ref);
                    this.updateActiveVisible();
                },
            },
        });
    }

    scrollToActive() {
        this.activeRef.el?.scrollIntoView(true);
    }

    updateActiveVisible() {
        if (!this.activeRef?.el) {
            this.state.activeVisibility = null;
        }
        if (this.activeVisible.isVisible) {
            this.state.activeVisibility = ACTIVE_VISIBILITY.VISIBLE;
            return;
        }
        const activeTop = this.activeRef.el.getBoundingClientRect().top;
        const rootTop = this.root.el.getBoundingClientRect().top;
        if (activeTop < rootTop) {
            this.state.activeVisibility = ACTIVE_VISIBILITY.HIDDEN_TOP;
        } else {
            this.state.activeVisibility = ACTIVE_VISIBILITY.HIDDEN_BOTTOM;
        }
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }
}
