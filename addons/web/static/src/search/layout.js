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
        const { display = {} } = this.env.searchModel || {};
        this.components = extractLayoutComponents(this.env.config);
        if (display.controlPanel && this.env.inDialog) {
            display.controlPanel["top-left"] = false;
            display.controlPanel["bottom-left-buttons"] = false;
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
    slots: { type: Object, optional: true },
};
