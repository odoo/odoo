/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export const SHOW_OPTIONS = {
    type: Object,
    shape: {
        uom: Boolean,
        replenishments: Boolean,
        availabilities: Boolean,
        receipts: Boolean,
        unitCosts: Boolean,
        moCosts: Boolean,
        realCosts: Boolean,
    },
};

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
            unitCosts: _t("Unit Costs"),
            moCosts: _t("MO Costs"),
            realCosts: _t("Real Costs"),
        };
    }
}

MoOverviewDisplayFilter.props = {
    showOptions: SHOW_OPTIONS,
    changeDisplay: Function,
    limited: { type: Boolean, optional: true },
};
MoOverviewDisplayFilter.defaultProps = {
    limited: false,
};
