declare module "@spreadsheet" {
    import { Model } from "@odoo/o-spreadsheet";

    export interface OdooSpreadsheetModel extends Model {
        getters: OdooGetters;
        dispatch: OdooDispatch;
    }

    export interface OdooSpreadsheetModelConstructor {
        new (
            data: object,
            config: Partial<Model["config"]>,
            revisions: object[]
        ): OdooSpreadsheetModel;
    }
}
