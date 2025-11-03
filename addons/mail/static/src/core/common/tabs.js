import { useChildRefs, useForwardRefsToParent } from "@mail/utils/common/hooks";
import { Component, reactive, useChildSubEnv, useRef, useState, xml } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

/**
 * @typedef {Object} Props
 * @property {any} [initialTabId] Id of the tab that should be active at the start.
 * @property {"v"|"h"} [direction] Direction of the tabs. "v" for vertical, "h" for horizontal.
 * @property {ReturnType<typeof import("@web/core/utils/hooks").useChildRef>} [tabsRef] Ref function returned
 * by `useChildRef`. Used to forward the Tabs component ref to its parent.
 * @property {Record<string, any>} [slots]
 * @extends {Component<Props, Env>}
 */
export class Tabs extends Component {
    static template = "mail.Tabs";
    static props = ["initialTabId?", "direction?", "tabsRef?", "slots?"];
    static defaultProps = { direction: "v" };

    setup() {
        this.state = useState({
            activeTabId: this.props.initialTabId,
            indicatorH: 0,
            indicatorW: 0,
            indicatorX: 0,
            indicatorY: 0,
        });
        this.updateActiveTab = useDebounced(() => {
            let targetTabId;
            if (this.headerRefs.has(this.state.activeTabId)) {
                targetTabId = this.state.activeTabId;
            } else {
                const indexToTabId = {};
                for (const [tabId, ref] of this.headerRefs.entries()) {
                    indexToTabId[ref.el.dataset.index] = tabId;
                }
                targetTabId = indexToTabId[Math.min(...Object.keys(indexToTabId))];
            }
            this.setActiveTab(this.headerRefs.get(targetTabId)?.el, targetTabId);
        });
        this.headerRefs = reactive(useChildRefs(), () => this.updateActiveTab());
        void this.headerRefs.size;
        useForwardRefToParent("tabsRef");
        useChildSubEnv({
            tabsContext: {
                headerRefs: this.headerRefs,
                isActive: (id) => this.state.activeTabId === id,
                setActiveTab: (headerEl, id) => this.setActiveTab(headerEl, id),
            },
        });
    }

    setActiveTab(headerEl, id) {
        this.state.activeTabId = id;
        if (this.props.direction === "v") {
            this.state.indicatorY = headerEl?.offsetTop ?? 0;
            this.state.indicatorH = headerEl?.offsetHeight ?? 0;
            this.state.indicatorW = 3;
            this.state.indicatorX = 0;
        } else {
            this.state.indicatorX = headerEl?.offsetLeft ?? 0;
            this.state.indicatorW = headerEl?.offsetWidth ?? 0;
            this.state.indicatorH = 3;
            this.state.indicatorY = 0;
        }
    }
}

const TAB_HEADER_PROPS = ["id", "index", "title?", "slots?"];
export class InternalTabHeader extends Component {
    static template = "mail.InternalTabHeader";
    static props = [...TAB_HEADER_PROPS, "headerRefs"];

    setup() {
        super.setup(...arguments);
        this.root = useRef("root");
        useForwardRefsToParent("headerRefs", (props) => props.id, this.root);
    }

    onClick() {
        this.env.tabsContext.setActiveTab(this.root.el, this.props.id);
    }

    get isActive() {
        return this.env.tabsContext.isActive(this.props.id);
    }
}

/**
 * Owl doesn’t support dynamic slot names (`t-set-slot`). Tabs therefore define
 * two static slots: one for headers and one for content. To manage header refs
 * internally, we use `useForwardRefsToParent`. `TabHeader` is a thin wrapper
 * around `InternalTabHeader` that forwards these refs while keeping the external
 * API simple.
 */
export class TabHeader extends Component {
    static template = xml`<InternalTabHeader id="props.id" title="props.title" default="props.default" index="props.index" headerRefs="env.tabsContext.headerRefs"><t t-slot="default"/></InternalTabHeader>`;
    static components = { InternalTabHeader };
    static props = TAB_HEADER_PROPS;
}

export class TabPanel extends Component {
    static template = "mail.TabPanel";
    static props = ["id", "slots?"];
}
