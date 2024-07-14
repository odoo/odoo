/** @odoo-module */
import * as spreadsheet from "@odoo/o-spreadsheet";

import { Component } from "@odoo/owl";
const { Menu } = spreadsheet;

export class FilterComponent extends Component {
    get activeFilter() {
        return this.env.model.getters.getActiveFilterCount();
    }

    toggleDropdown() {
        this.env.toggleSidePanel("GLOBAL_FILTERS_SIDE_PANEL");
    }
}

FilterComponent.template = "spreadsheet_edition.FilterComponent";

FilterComponent.components = { Menu };

FilterComponent.props = {};
