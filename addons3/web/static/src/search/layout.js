/** @odoo-module **/

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
    if (params.Banner) {
        layoutComponents.Banner = params.Banner;
    }
    return layoutComponents;
}

export class Layout extends Component {
    setup() {
        this.components = extractLayoutComponents(this.env.config);
        this.contentRef = useRef("content");
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        delete slots.default;
        return slots;
    }
    get display() {
        const { controlPanel } = this.props.display;
        if (!controlPanel || !this.env.inDialog) {
            return this.props.display;
        }
        return {
            ...this.props.display,
            controlPanel,
        };
    }
}

Layout.template = "web.Layout";
Layout.props = {
    className: { type: String, optional: true },
    display: { type: Object, optional: true },
    slots: { type: Object, optional: true },
};
Layout.defaultProps = {
    display: {},
};
