import { useChildRefs, useForwardRefsToParent, useScrollState } from "@mail/utils/common/hooks";
import { Component, useChildSubEnv, useEffect, useRef, useState, xml } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {"v"|"h"} [direction] Direction of the tabs. "v" for vertical, "h" for horizontal.
 * @property {any} [initialTabId] Id of the tab that should be active at the start.
 * @property {ReturnType<typeof import("@web/core/utils/hooks").useChildRef>} [ref] Ref function returned
 * by `useChildRef`. Used to forward the Tabs component ref to its parent.
 * @property {Record<string, any>} [slots]
 * @extends {Component<Props, Env>}
 */
export class Tabs extends Component {
    static template = "mail.Tabs";
    static props = {
        direction: { type: String, optional: true, validate: (d) => ["v", "h"].includes(d) },
        initialTabId: { type: String, optional: true },
        ref: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = { direction: "v" };

    setup() {
        this.state = useState({ activeHeaderId: this.props.initialTabId });
        this.headerRefs = useChildRefs();
        this.navRef = useRef("nav");
        this.scrollState = useScrollState("nav");
        useForwardRefToParent("ref");
        useChildSubEnv({
            tabsContext: {
                headerRefs: this.headerRefs,
                isActive: (id) => this.state.activeHeaderId === id,
                setActiveTab: (id) => (this.state.activeHeaderId = id),
            },
        });
        useEffect(
            (refs, headerEls, activeHeaderId) => {
                if (!refs.has(activeHeaderId) && headerEls) {
                    this.state.activeHeaderId = headerEls[0].dataset.headerId;
                }
            },
            () => [
                this.headerRefs,
                this.navRef.el?.children,
                this.state.activeHeaderId,
                this.headerRefs.size,
            ]
        );
    }

    /**
     * Scrolls the tab navigation container by one full viewport (page/panel).
     *
     * @param {number} direction The direction to scroll (1 for forward, -1 for backward).
     */
    async scroll(direction) {
        const navEl = this.navRef.el;
        if (this.props.direction === "v") {
            navEl?.scrollBy({ top: navEl?.clientHeight * direction, behavior: "smooth" });
        } else {
            navEl?.scrollBy({ left: navEl?.clientWidth * direction, behavior: "smooth" });
        }
    }
}

const TAB_HEADER_PROPS = ["id", "title?", "slots?"];
export class InternalTabHeader extends Component {
    static template = "mail.InternalTabHeader";
    static props = [...TAB_HEADER_PROPS, "headerRefs"];

    setup() {
        super.setup(...arguments);
        this.root = useRef("root");
        useForwardRefsToParent("headerRefs", (props) => props.id, this.root);
    }

    onClick() {
        this.env.tabsContext.setActiveTab(this.props.id);
    }

    get isActive() {
        return this.env.tabsContext.isActive(this.props.id);
    }
}

/**
 * Owl doesn’t support dynamic slot names (`t-set-slot`). Tabs therefore define
 * two static slots: one for the headers and one for the content. To manage header
 * refs internally, we use `useForwardRefsToParent`. `TabHeader` is a thin wrapper
 * around `InternalTabHeader` that forwards these refs while keeping the external
 * API simple.
 */
export class TabHeader extends Component {
    static template = xml`<InternalTabHeader id="props.id" title="props.title" headerRefs="env.tabsContext.headerRefs"><t t-slot="default"/></InternalTabHeader>`;
    static components = { InternalTabHeader };
    static props = TAB_HEADER_PROPS;
}

export class TabPanel extends Component {
    static template = "mail.TabPanel";
    static props = ["id", "slots?"];
}
