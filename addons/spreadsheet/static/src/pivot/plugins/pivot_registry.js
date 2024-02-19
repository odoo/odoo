import { Registry } from "@odoo/o-spreadsheet";
import { OdooPivot } from "../pivot_data_source";

export const pivotRegistry = new Registry();

pivotRegistry.add("ODOO", OdooPivot);
