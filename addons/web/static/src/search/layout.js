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
        const display = this.props.display;
        if (display.controlPanel && this.env.inDialog) {
            display.controlPanel = Object.assign({}, display.controlPanel, {
                "top-left": false,
                "bottom-left-buttons": false,
            });
        }
        this.display = display;
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        slots["control-panel-bottom-left-buttons"] = slots["layout-buttons"];
        delete slots["layout-buttons"];
        delete slots.default;
        return slots;
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
