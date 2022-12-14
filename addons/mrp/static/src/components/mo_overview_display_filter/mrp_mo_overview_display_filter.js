/** @odoo-module **/
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export class MoOverviewDisplayFilter extends BomOverviewDisplayFilter {
    setup() {
        this.displayOptions = {
            replenishments: this.env._t("Replenishments"),
            availabilities: this.env._t("Availabilities"),
            receipts: this.env._t("Receipts"),
            moCosts: this.env._t("MO Costs"),
            productCosts: this.env._t("Product Costs"),
        };
    }
}

MoOverviewDisplayFilter.props = {
    showOptions: {
        type: Object,
        shape: {
            uom: Boolean,
            replenishments: Boolean,
            availabilities: Boolean,
            receipts: Boolean,
            moCosts: Boolean,
            productCosts: Boolean,
        }
    },
    changeDisplay: Function,
};
