/** @odoo-module */

import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component } from "@odoo/owl";

export class InsertListSpreadsheetMenu extends Component {
    /**
     * @private
     */
    _onClick() {
        this.env.bus.trigger("insert-list-spreadsheet");
    }
}

InsertListSpreadsheetMenu.props = {};
InsertListSpreadsheetMenu.template = "spreadsheet_edition.InsertListSpreadsheetMenu";
InsertListSpreadsheetMenu.components = { DropdownItem };
