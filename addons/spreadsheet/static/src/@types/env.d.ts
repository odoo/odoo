import { SpreadsheetChildEnv } from "@odoo/o-spreadsheet";
import { Services } from "services";

declare module "@spreadsheet" {
  import { Model } from "@odoo/o-spreadsheet";

  export interface SpreadsheetChildEnv extends SpreadsheetChildEnv {
    model: OdooSpreadsheetModel;
    services: Services;
  }

}
