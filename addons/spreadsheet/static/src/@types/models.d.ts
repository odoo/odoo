
declare module "@spreadsheet" {
  import { Model } from "@odoo/o-spreadsheet";

  export interface OdooSpreadsheetModel extends Model {
    getters: OdooGetters;
  }

  export interface OdooSpreadsheetModelConstructor {
    new(data: object, config: Model["config"]): OdooSpreadsheetModel;
  }

}
