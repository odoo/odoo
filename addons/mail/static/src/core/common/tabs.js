import { useChildSubEnv, useLayoutEffect } from "@web/owl2/utils";
import { useScrollState } from "@mail/utils/common/hooks";
import { Component, props, Resource, signal, t, useEffect, xml } from "@odoo/owl";

export class Tabs extends Component {
    static template = "mail.Tabs";

    setup() {
        this.props = props({
            direction: t.selection(["h", "v"]).optional("v"),
            initialTabId: t.or([t.string(), t.number()]).optional(),
            ref: t.signal(t.ref()).optional(() => signal.ref()),
        });
        this.activeHeaderId = signal(this.props.initialTabId);
        /** Header elements, each `TabHeader` binding its own with `t-ref`. */
        this.headerEls = new Resource({
            name: "tabHeaders",
            validation: t.instanceOf(HTMLElement),
        });
        this.navRef = signal();
        this.scrollState = useScrollState(this.navRef);
        useChildSubEnv({
            tabsContext: {
                headerEls: this.headerEls,
                isActive: (id) => this.activeHeaderId() === id,
                setActiveTab: (id) => this.activeHeaderId.set(id),
            },
        });
        useEffect(() => {
            const headerEls = this.navRef()?.children;
            if (!this.hasHeader(this.activeHeaderId()) && headerEls?.length) {
                this.activeHeaderId.set(headerEls[0].dataset.headerId);
            }
        });
    }

    /**
     * @param {string|number} id
     * @returns {boolean} whether a header with the given id is currently mounted
     */
    hasHeader(id) {
        return this.headerEls.items().some((el) => el.dataset.headerId === String(id));
    }

    /**
     * Scrolls the tab navigation container by one full viewport (page/panel).
     *
     * @param {number} direction The direction to scroll (1 for forward, -1 for backward).
     */
    async scroll(direction) {
        const navEl = this.navRef();
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
            headerEls: t.instanceOf(Resource),
            id: t.or([t.string(), t.number()]),
            title: t.string().optional(),
        });
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
 * two static slots: one for the headers and one for the content. To gather header
 * elements internally, `Tabs` owns a resource that each header binds with `t-ref`.
 * `TabHeader` is a thin wrapper around `InternalTabHeader` that forwards this
 * resource while keeping the external API simple.
 */
export class TabHeader extends Component {
    static template = xml`<InternalTabHeader id="this.props.id" title="this.props.title" headerEls="this.env.tabsContext.headerEls"><t t-call-slot="default"/></InternalTabHeader>`;
    static components = { InternalTabHeader };

    setup() {
        super.setup(...arguments);
        this.props = props({
            id: t.any(),
            title: t.string().optional(),
        });
    }
}

export class TabPanel extends Component {
    static template = "mail.TabPanel";

    setup() {
        super.setup();
        this.props = props({
            id: t.any(),
            onBecameVisible: t.function([]).optional(),
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
