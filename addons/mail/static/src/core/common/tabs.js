import { useChildSubEnv, useLayoutEffect } from "@web/owl2/utils";
import { useChildRefs, useForwardRefsToParent, useScrollState } from "@mail/utils/common/hooks";
import { Component, props, signal, types, useEffect, xml } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class Tabs extends Component {
    static template = "mail.Tabs";

    setup() {
        this.props = props(
            {
                "direction?": types.selection(["h", "v"]),
                "initialTabId?": types.or([types.string(), types.number()]),
                "ref?": types.function(),
            },
            { direction: "v" }
        );
        this.activeHeaderId = signal(this.props.initialTabId);
        this.headerRefs = useChildRefs();
        this.navRef = signal();
        this.scrollState = useScrollState(this.navRef);
        useForwardRefToParent("ref");
        useChildSubEnv({
            tabsContext: {
                headerRefs: this.headerRefs,
                isActive: (id) => this.activeHeaderId() === id,
                setActiveTab: (id) => this.activeHeaderId.set(id),
            },
        });
        useEffect(() => {
            const headerEls = this.navRef()?.children;
            if (!this.headerRefs.has(this.activeHeaderId()) && headerEls?.length) {
                this.activeHeaderId.set(headerEls[0].dataset.headerId);
            }
        });
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

export class InternalTabHeader extends Component {
    static template = "mail.InternalTabHeader";

    setup() {
        super.setup(...arguments);
        this.props = props({
            headerRefs: types.object(),
            id: types.or([types.string(), types.number()]),
            "title?": types.string(),
        });
        this.rootRef = signal();
        useForwardRefsToParent("headerRefs", (props) => props.id, this.rootRef);
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
    static template = xml`<InternalTabHeader id="this.props.id" title="this.props.title" headerRefs="this.env.tabsContext.headerRefs"><t t-call-slot="default"/></InternalTabHeader>`;
    static components = { InternalTabHeader };

    setup() {
        super.setup(...arguments);
        this.props = props({
            id: types.any(),
            "title?": types.string(),
        });
    }
}

export class TabPanel extends Component {
    static template = "mail.TabPanel";

    setup() {
        super.setup();
        this.props = props({
            id: types.any(),
            "onBecameVisible?": types.function([]),
        });
        useLayoutEffect(
            (active) => {
                if (active) {
                    this.props.onBecameVisible?.();
                }
            },
            () => [this.env.tabsContext.isActive(this.props.id)]
        );
    }
}
