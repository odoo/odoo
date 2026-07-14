/** @odoo-module */

import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { Spreadsheet, Model } from "@odoo/o-spreadsheet";
import { Component } from "@odoo/owl";

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
    }
}
