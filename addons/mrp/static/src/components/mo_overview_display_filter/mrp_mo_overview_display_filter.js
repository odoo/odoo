/** @odoo-module **/
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export class MoOverviewDisplayFilter extends BomOverviewDisplayFilter {
    setup() {
        if (!this.props.limited) {
            this.displayOptions = {
                replenishments: this.env._t("Replenishments"),
                availabilities: this.env._t("Availabilities"),
                receipts: this.env._t("Receipts"),
            };
        }
        this.displayOptions = {
            ...(this.displayOptions || {}),
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
        },
    },
    changeDisplay: Function,
    limited: { type: Boolean, optional: true },
};
MoOverviewDisplayFilter.defaultProps = {
    limited: false,
};
