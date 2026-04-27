/** @odoo-module */

import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component } from "@odoo/owl";

export class InsertListSpreadsheetMenu extends Component {
    static props = {};
    static template = "spreadsheet_edition.InsertListSpreadsheetMenu";
    static components = { DropdownItem };

    /**
     * @private
     */
    _onClick() {
        this.env.bus.trigger("insert-list-spreadsheet");
    }
}
