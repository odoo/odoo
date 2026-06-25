import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { Spreadsheet, Model, stores } from "@odoo/o-spreadsheet";
import { Component } from "@odoo/owl";

const { useStoreProvider, useStore, ViewportsStore, ModelStore } = stores;

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
        registerStoreProvider: { type: Function, optional: true },
    };

    get model() {
        return this.props.model;
    }
    setup() {
        useSpreadsheetNotificationStore();

        const stores = useStoreProvider();
        stores.inject(ModelStore, this.model);
        this.viewStore = useStore(ViewportsStore);
        this.props.registerStoreProvider?.(stores);
    }
}
