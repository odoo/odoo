/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchPanel } from "@web/search/search_panel/search_panel";

const { Component } = owl;

/**
 * @param {Object} params
 * @returns {Object}
 */
export const extractLayoutComponents = (params) => {
    return {
        ControlPanel: params.ControlPanel || ControlPanel,
        SearchPanel: params.SearchPanel || SearchPanel,
        Banner: params.Banner || false,
    };
};

export class Layout extends Component {
    setup() {
        const { display = {} } = this.env.searchModel || {};
        this.components = extractLayoutComponents(this.env.config);
        if (this.env.inDialog) {
            display.controlPanel["top-left"] = false;
            display.controlPanel["bottom-left"] = false;
        }
        this.display = display;
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        delete slots.default;
        return slots;
    }
}

Layout.template = "web.Layout";
Layout.props = {
    className: { type: String, optional: true },
    slots: { type: Object, optional: true },
};
