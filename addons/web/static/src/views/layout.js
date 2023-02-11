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
}

Layout.template = "web.Layout";
Layout.props = {
    viewType: { type: String, optional: true },
    useSampleModel: { type: Boolean, optional: true },
};
