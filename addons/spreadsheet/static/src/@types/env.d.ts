import { SpreadsheetChildEnv as SSChildEnv } from "@odoo/o-spreadsheet";
import { Services } from "services";

declare module "@spreadsheet" {
    import { Model } from "@odoo/o-spreadsheet";

    export interface SpreadsheetChildEnv extends SSChildEnv {
        model: OdooSpreadsheetModel;
        services: Services;
    }
}
