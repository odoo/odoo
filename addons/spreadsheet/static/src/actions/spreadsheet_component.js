/** @odoo-module */

import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { Spreadsheet, Model } from "@odoo/o-spreadsheet";
import { Component, onWillUnmount } from "@odoo/owl";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";

/**
 * Component wrapping the <Spreadsheet> component from o-spreadsheet
 * to add user interactions extensions from odoo such as notifications,
 * error dialogs, etc.
 */
export class SpreadsheetComponent extends Component {
    static template = "spreadsheet.SpreadsheetComponent";
    static components = { Spreadsheet };
    static props = {
        model: Model,
    };

    get model() {
        return this.props.model;
    }

    setup() {
        useSpreadsheetNotificationStore();
        onWillUnmount(() => {
            for (const key in globalFiltersFieldMatchers) {
                delete globalFiltersFieldMatchers[key];
            }
        });
    }
}
