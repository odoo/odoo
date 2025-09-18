// @ts-check

/** @module @web/search/layout - Top-level view layout assembling ControlPanel, SearchPanel, and content slots */

import { Component, useRef } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchPanel } from "@web/search/search_panel/search_panel";

/**
 * @param {Object} params
 * @returns {Object}
 */
export function extractLayoutComponents(params) {
    const layoutComponents = {
        ControlPanel: params.ControlPanel || ControlPanel,
        SearchPanel: params.SearchPanel || SearchPanel,
    };
    return layoutComponents;
}

/** Top-level view layout that assembles ControlPanel, SearchPanel, and content slots. */
export class Layout extends Component {
    static template = "web.Layout";
    static props = {
        className: { type: String, optional: true },
        display: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        display: {},
    };
    setup() {
        this.components = extractLayoutComponents(this.env.config);
        this.contentRef = useRef("content");
    }
    /** @returns {Object} slots forwarded to the ControlPanel, excluding `default` and `layout-buttons` in dialogs */
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        if (this.env.inDialog) {
            delete slots["layout-buttons"];
        }
        delete slots.default;
        return slots;
    }
}
