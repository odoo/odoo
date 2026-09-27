import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
import { useChildRefs, useScrollState } from "@mail/utils/common/hooks";
import { Component, Portal, signal, t, useEffect, useProps } from "@odoo/owl";

export class Tabs extends Component {
    static template = "mail.Tabs";

    setup() {
        this.props = useProps({
            direction: t.selection(["h", "v"]).optional("v"),
            initialTabId: t.or([t.string(), t.number()]).optional(),
        });
        /** Root element, either owned by the parent (`ref` prop) or local. */
        this.rootRef = useProps.static(
            "ref",
            t.signal(t.ref()).optional(() => signal.ref())
        );
        this.activeHeaderId = signal(this.props.initialTabId);
        this.headerRefs = useChildRefs();
        this.navRef = signal();
        this.scrollState = useScrollState(this.navRef);
        useSubEnv({
            tabsContext: {
                navRef: this.navRef,
                headerRefs: this.headerRefs,
                isActive: (id) => this.activeHeaderId() === id,
                setActiveTab: (id) => this.activeHeaderId.set(id),
            },
        });
        useEffect(() => {
            if (!this.headerRefs.has(this.activeHeaderId()) && this.headerRefs.size) {
                this.activeHeaderId.set(this.headerRefs.keys().next().value);
            }
        });
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

/**
 * One tab inside the `Tabs` component. The `header` slot is rendered in the tabs' navbar
 * while the content is displayed in place when this tab is the active one.
 */
export class Tab extends Component {
    static template = "mail.Tab";
    static components = { Portal };

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            id: t.or([t.string(), t.number()]),
            title: t.string().optional(),
            onBecameVisible: t.function([]).optional(),
        });
        this.rootRef = signal();
        useLayoutEffect(
            (headerRefs, id) => {
                headerRefs.set(id, this.rootRef);
                return () => headerRefs.delete(id);
            },
            () => [this.env.tabsContext.headerRefs, this.props.id]
        );
        useLayoutEffect(
            (active) => {
                if (active) {
                    this.props.onBecameVisible?.();
                }
            },
            () => [this.isActive]
        );
    }

    onClick() {
        this.env.tabsContext.setActiveTab(this.props.id);
    }

    get isActive() {
        return this.env.tabsContext.isActive(this.props.id);
    }
}
