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
        this.display = display;
    }
    get className() {
        const classes = this.props.className.split(" ");
        if (this.props.useSampleModel) {
            classes.push("o_view_sample_data");
        }
        if (this.props.viewType) {
            classes.push(`o_${this.props.viewType}_view`);
        }
        return classes.join(" ");
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        delete slots.default;
        return slots;
    }
}

Layout.template = "web.Layout";
Layout.defaultProps = { className: "" };
Layout.props = {
    className: { type: String, optional: true },
    slots: { type: Object, optional: true },
    viewType: { type: String, optional: true },
    useSampleModel: { type: Boolean, optional: true },
};
