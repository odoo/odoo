/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export class MoOverviewDisplayFilter extends BomOverviewDisplayFilter {
    setup() {
        if (!this.props.limited) {
            this.displayOptions = {
                replenishments: _t("Replenishments"),
                availabilities: _t("Availabilities"),
                receipts: _t("Receipts"),
            };
        }
        this.displayOptions = {
            ...(this.displayOptions || {}),
            moCosts: _t("MO Costs"),
            productCosts: _t("Product Costs"),
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
