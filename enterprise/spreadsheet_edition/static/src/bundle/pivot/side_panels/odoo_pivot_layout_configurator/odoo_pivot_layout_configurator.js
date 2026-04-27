import { components } from "@odoo/o-spreadsheet";
import { ODOO_AGGREGATORS } from "@spreadsheet/pivot/pivot_helpers";
const { PivotLayoutConfigurator } = components;

export class OdooPivotLayoutConfigurator extends PivotLayoutConfigurator {
    setup() {
        super.setup(...arguments);
        this.AGGREGATORS = ODOO_AGGREGATORS;
    }
}
