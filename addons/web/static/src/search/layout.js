/** @odoo-module **/

import { pick } from "@web/core/utils/objects";

const { Component } = owl;

/**
 * @param {Object} params
 * @returns {Object}
 */
export function extractLayoutComponents(params) {
    return pick(params, "ControlPanel", "SearchPanel", "Banner");
}

export class Layout extends Component {
    setup() {
        this.components = extractLayoutComponents(this.env.config);
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        slots["control-panel-bottom-left-buttons"] = slots["layout-buttons"];
        delete slots["layout-buttons"];
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
            controlPanel: {
                ...controlPanel,
                "top-left": false,
                "bottom-left-buttons": false,
            },
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
