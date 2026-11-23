import { useSpreadsheetNotificationPlugin } from "@spreadsheet/hooks";
import { Spreadsheet, Model } from "@odoo/o-spreadsheet";
import { Component, t, useProps } from "@odoo/owl";

/**
 * Component wrapping the <Spreadsheet> component from o-spreadsheet
 * to add user interactions extensions from odoo such as notifications,
 * error dialogs, etc.
 */
export class SpreadsheetComponent extends Component {
    static template = "spreadsheet.SpreadsheetComponent";
    static components = { Spreadsheet };
    props = useProps({
        model: t.instanceOf(Model),
    });

    get model() {
        return this.props.model;
    }
    setup() {
        useSpreadsheetNotificationPlugin();
    }
}
