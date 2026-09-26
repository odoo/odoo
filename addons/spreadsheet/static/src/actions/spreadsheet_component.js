import { useSpreadsheetNotificationPlugin } from "@spreadsheet/hooks";
import { Spreadsheet, Model, stores, owlPlugins } from "@odoo/o-spreadsheet";
import { Component, t, useProps, providePlugins } from "@odoo/owl";

const { useStoreProvider, useStore, ViewportsStore, ModelStore } = stores;
const { ModelPlugin } = owlPlugins;

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
        registerStoreProvider: t.function().optional(),
    });

    get model() {
        return this.props.model;
    }
    setup() {
        useSpreadsheetNotificationPlugin();
        providePlugins([ModelPlugin], { model: this.model });

        if (this.props.registerStoreProvider) {
            const stores = useStoreProvider();
            stores.inject(ModelStore, this.model);
            this.viewStore = useStore(ViewportsStore);
            this.props.registerStoreProvider(stores);
        }
    }
}
